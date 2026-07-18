from fragility_map.model.stress import CompanyFinancials, NetworkRelationship, ScenarioResult


def build_graph_payload(
    companies: dict[str, CompanyFinancials],
    relationships: list[NetworkRelationship],
    scenario_result: ScenarioResult,
) -> dict:
    return {
        "nodes": [
            {
                "data": {
                    "id": company.company_id,
                    "label": company.name,
                    "sectorGroup": company.sector_group,
                    "revenue": company.revenue,
                    "revenueLoss": scenario_result.company_impacts[company.company_id].revenue_loss,
                    "stressStatus": scenario_result.company_impacts[
                        company.company_id
                    ].stress_status,
                }
            }
            for company in companies.values()
        ],
        "edges": [
            {
                "data": {
                    "id": relationship.relationship_id,
                    "source": relationship.buyer_company_id,
                    "target": relationship.seller_company_id,
                    "annualFlowBase": relationship.annual_flow_base,
                    "confidenceScore": relationship.confidence_score,
                    "estimateMethod": relationship.estimation_method,
                }
            }
            for relationship in relationships
        ],
        "pulses": [
            {
                "relationshipId": pulse.relationship_id,
                "source": pulse.buyer_company_id,
                "target": pulse.seller_company_id,
                "roundIndex": pulse.round_index,
                "revenueLoss": pulse.revenue_loss,
            }
            for pulse in scenario_result.edge_pulses
        ],
        "summary": {
            "scenarioLanguage": "estimated impact under scenario",
            "totalRevenueLost": sum(
                impact.revenue_loss for impact in scenario_result.company_impacts.values()
            ),
            "stressedCompanyCount": sum(
                1
                for impact in scenario_result.company_impacts.values()
                if impact.stress_status in {"stressed", "critical"}
            ),
        },
    }
