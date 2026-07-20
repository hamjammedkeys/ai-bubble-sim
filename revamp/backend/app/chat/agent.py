"""FragilityGraph copilot: an OpenAI tool-calling agent over the existing services.

The agent never invents numbers — it acts only through tools that read/write the
same graph the UI uses (ingest a filing, summarize the graph, create/run a
scenario). `client` is injectable so the loop is testable without a network.
"""

import json

from sqlalchemy.orm import Session

from app.chat.filing_search import rank_passages
from app.config import settings
from app.extraction.adapter import extract_document_candidates
from app.ingestion import fetch_url_text
from app.models import Document, Edge, Entity, Scenario
from app.services.candidates import persist_candidates
from app.services.scenarios import run_and_store

CHAT_SYSTEM = (
    "You are the FragilityGraph copilot. You help the user analyze disclosed financial "
    "exposure between AI-economy companies, sourced from SEC filings. Act only through the "
    "provided tools — never invent figures. You can: summarize the current graph, ingest a "
    "filing from a URL (which extracts candidate edges for the user to review), create a "
    "shock scenario on an existing company, and run a scenario. When the user wants to model "
    "a shock, create the scenario (origin_entity must be one of the companies in the graph) "
    "and run it, then explain the result honestly: 'impact' is a forced accounting loss "
    "(equity-method share of a disclosed net loss); 'exposure' is an amount placed at risk, "
    "NOT a realized loss (realizing it needs undisclosed PD/LGD/EAD); 'unresolved' edges have "
    "no disclosed propagation so no number is invented. "
    "To answer a question about what a filing SAYS (risk factors, segments, guidance, any "
    "prose), first call find_filings to locate the relevant document, then search_filing to "
    "retrieve passages. Answer ONLY from the returned passages: quote the exact wording, name "
    "the source document, and if the passages do not cover the question say the filing does not "
    "disclose it — never fill the gap from general knowledge. Keep replies concise and specific."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "graph_summary",
            "description": "List the companies and their edges (relationships, values, status) in the current graph.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ingest_filing",
            "description": "Read an SEC filing (or any page) from a URL and extract candidate edges for review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The filing URL."},
                    "title": {"type": "string", "description": "Optional human title."},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_filings",
            "description": "List ingested filings (id, title, company, type, url) so you can pick which one to search.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_filing",
            "description": (
                "Retrieve the passages of an ingested filing most relevant to a query, to quote "
                "and cite. Omit document_id to search across all filings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to look for, e.g. 'risk factors'."},
                    "document_id": {"type": "string", "description": "Restrict to one filing (optional)."},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_scenario",
            "description": "Create a shock scenario originating at one company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "origin_entity": {"type": "string", "description": "A company name already in the graph."},
                    "magnitude": {"type": "number", "description": "Shock size, e.g. a GAAP loss in USD billions."},
                    "unit": {"type": "string"},
                },
                "required": ["name", "origin_entity", "magnitude"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_scenario",
            "description": "Run a scenario by its name and return separated impact/exposure totals.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
]


def _tool_impls(session: Session) -> dict:
    def graph_summary() -> dict:
        entities = [{"name": e.name, "type": e.entity_type} for e in session.query(Entity).all()]
        names = {e.id: e.name for e in session.query(Entity).all()}
        edges = [
            {
                "source": names.get(e.source_entity_id),
                "target": names.get(e.target_entity_id),
                "relationship": e.relationship_type,
                "value": e.value,
                "unit": e.unit,
                "status": e.status,
            }
            for e in session.query(Edge).all()
        ]
        return {"companies": entities, "edges": edges}

    def ingest_filing(url: str, title: str | None = None) -> dict:
        text = fetch_url_text(url)
        doc = Document(title=title or url, url=url, raw_text=text)
        session.add(doc)
        session.commit()
        session.refresh(doc)
        known = [n for (n,) in session.query(Entity.name).all()]
        result = extract_document_candidates(
            doc.raw_text,
            known,
            document_id=doc.id,
            provider=settings.llm_provider,
            filing_entity=doc.company,
        )
        edges = persist_candidates(session, result, doc)
        return {"document_id": doc.id, "title": doc.title, "candidates_created": len(edges)}

    def find_filings() -> dict:
        docs = session.query(Document).order_by(Document.ingested_at.desc()).limit(25).all()
        return {
            "filings": [
                {
                    "document_id": d.id,
                    "title": d.title,
                    "company": d.company,
                    "filing_type": d.filing_type,
                    "url": d.url,
                    "chars": len(d.raw_text or ""),
                }
                for d in docs
            ]
        }

    def search_filing(query: str, document_id: str | None = None) -> dict:
        docs = (
            [session.get(Document, document_id)] if document_id else session.query(Document).all()
        )
        docs = [d for d in docs if d is not None]
        if not docs:
            return {"query": query, "passages": [], "note": "no matching filing found"}
        passages: list[dict] = []
        for doc in docs:
            for hit in rank_passages(doc.raw_text or "", query, limit=5):
                passages.append(
                    {
                        "document_id": doc.id,
                        "document_title": doc.title,
                        "snippet": hit["snippet"],
                        "score": hit["score"],
                    }
                )
        passages.sort(key=lambda p: p["score"], reverse=True)
        return {"query": query, "passages": passages[:6]}

    def create_scenario(name: str, origin_entity: str, magnitude: float, unit: str = "usd_billions") -> dict:
        scenario = Scenario(
            name=name,
            description=f"Shock originating at {origin_entity}.",
            shock_json={"origin_entity": origin_entity, "kind": "gaap_loss", "magnitude": magnitude, "unit": unit},
        )
        session.add(scenario)
        session.commit()
        session.refresh(scenario)
        return {"scenario_id": scenario.id, "name": name, "origin_entity": origin_entity, "magnitude": magnitude}

    def run_scenario(name: str) -> dict:
        scenario = session.query(Scenario).filter(Scenario.name == name).first()
        if scenario is None:
            return {"error": f"no scenario named '{name}'"}
        results, totals, _run = run_and_store(session, scenario)
        return {"totals": totals, "results": [r.model_dump() for r in results]}

    return {
        "graph_summary": graph_summary,
        "ingest_filing": ingest_filing,
        "find_filings": find_filings,
        "search_filing": search_filing,
        "create_scenario": create_scenario,
        "run_scenario": run_scenario,
    }


def run_chat(messages: list[dict], session: Session, *, client=None, max_steps: int = 6) -> dict:
    """Run the copilot loop. `messages` is the prior conversation (role/content).

    Returns {"reply": str, "actions": [{tool, args, result}, ...]}.
    """
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

    impls = _tool_impls(session)
    convo: list = [{"role": "system", "content": CHAT_SYSTEM}, *messages]
    actions: list[dict] = []

    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=convo,
            tools=TOOLS,
        )
        message = response.choices[0].message
        convo.append(message)
        if not getattr(message, "tool_calls", None):
            return {"reply": message.content or "", "actions": actions}
        for call in message.tool_calls:
            fn = impls.get(call.function.name)
            try:
                args = json.loads(call.function.arguments or "{}")
                result = fn(**args) if fn else {"error": f"unknown tool {call.function.name}"}
            except Exception as exc:  # surface tool failure back to the model
                result = {"error": str(exc)}
            actions.append({"tool": call.function.name, "args": args, "result": result})
            convo.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})

    return {"reply": "I stopped after several steps — please refine the request.", "actions": actions}
