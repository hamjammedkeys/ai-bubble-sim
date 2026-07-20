import types

from app.chat.agent import run_chat
from app.extraction.schema import ExtractionResult
from app.models import Document, Entity, Scenario


def _fake_client(scripted):
    """A stand-in whose .chat.completions.create returns each scripted message in turn."""
    calls = {"n": 0}

    class _Completions:
        def create(self, **kwargs):
            self.last_kwargs = kwargs
            msg = scripted[calls["n"]]
            calls["n"] += 1
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    completions = _Completions()
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))


def _tool_call(name, arguments):
    return types.SimpleNamespace(
        content=None,
        tool_calls=[types.SimpleNamespace(id="c1", function=types.SimpleNamespace(name=name, arguments=arguments))],
    )


def _final(text):
    return types.SimpleNamespace(content=text, tool_calls=None)


def test_chat_agent_creates_scenario_via_tool_then_replies(db_session):
    db_session.add(Entity(name="OpenAI", aliases=[]))
    db_session.commit()

    client = _fake_client(
        [
            _tool_call("create_scenario", '{"name": "10B OpenAI shock", "origin_entity": "OpenAI", "magnitude": 10}'),
            _final("Created a scenario modelling a $10B shock at OpenAI."),
        ]
    )
    result = run_chat(
        [{"role": "user", "content": "model a $10B shock at OpenAI"}],
        db_session,
        client=client,
    )

    assert "Created" in result["reply"]
    assert any(a["tool"] == "create_scenario" for a in result["actions"])
    assert db_session.query(Scenario).filter_by(name="10B OpenAI shock").count() == 1


def test_chat_agent_returns_direct_reply_without_tools(db_session):
    client = _fake_client([_final("The graph tracks 6 companies.")])
    result = run_chat([{"role": "user", "content": "hi"}], db_session, client=client)
    assert result["reply"] == "The graph tracks 6 companies."
    assert result["actions"] == []


def test_graph_summary_tool_reports_entities(db_session):
    db_session.add(Entity(name="CoreWeave", entity_type="cloud_provider", aliases=[]))
    db_session.commit()
    client = _fake_client([_tool_call("graph_summary", "{}"), _final("You have CoreWeave.")])
    result = run_chat([{"role": "user", "content": "what companies?"}], db_session, client=client)
    summary = next(a for a in result["actions"] if a["tool"] == "graph_summary")["result"]
    assert any(c["name"] == "CoreWeave" for c in summary["companies"])


def test_find_and_search_filing_return_cited_passages(db_session):
    db_session.add(
        Document(
            title="Acme 10-K",
            company="Acme",
            filing_type="10-K",
            url="https://www.sec.gov/acme-10k",
            raw_text=(
                "Item 1A. Risk Factors.\nWe depend on a small number of large customers; "
                "the loss of a major customer could materially harm our revenue."
            ),
        )
    )
    db_session.commit()

    client = _fake_client(
        [
            _tool_call("find_filings", "{}"),
            _tool_call("search_filing", '{"query": "risk factors"}'),
            _final("Acme's 10-K lists customer concentration as a key risk factor."),
        ]
    )
    result = run_chat(
        [{"role": "user", "content": "what are Acme's risk factors?"}],
        db_session,
        client=client,
    )

    found = next(a for a in result["actions"] if a["tool"] == "find_filings")["result"]
    assert any(f["title"] == "Acme 10-K" for f in found["filings"])

    searched = next(a for a in result["actions"] if a["tool"] == "search_filing")["result"]
    assert searched["passages"], "expected cited passages"
    top = searched["passages"][0]
    assert top["document_title"] == "Acme 10-K"
    assert "customer" in top["snippet"].lower()


def test_ingest_filing_uses_document_level_orchestrator(db_session, monkeypatch):
    from app.chat import agent

    db_session.add_all([Entity(name="Amazon", aliases=[]), Entity(name="Anthropic", aliases=[])])
    db_session.commit()
    raw_text = "A" * 130_000 + "Amazon invested $8 billion in Anthropic."
    seen = {}

    monkeypatch.setattr(agent, "fetch_url_text", lambda _url: raw_text)

    def fake_extract(text, known_entities, document_id="doc", **kwargs):
        seen.update(
            text=text,
            known_entities=known_entities,
            document_id=document_id,
            kwargs=kwargs,
        )
        return ExtractionResult(candidates=[])

    monkeypatch.setattr(agent, "extract_document_candidates", fake_extract)
    client = _fake_client(
        [
            _tool_call("ingest_filing", '{"url": "https://www.sec.gov/amazon-10k"}'),
            _final("Filing ingested."),
        ]
    )

    result = run_chat(
        [{"role": "user", "content": "ingest Amazon's 10-K"}],
        db_session,
        client=client,
    )

    assert result["reply"] == "Filing ingested."
    assert seen["text"] == raw_text
    assert set(seen["known_entities"]) == {"Amazon", "Anthropic"}
    assert seen["document_id"] != "doc"
