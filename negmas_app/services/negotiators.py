"""Negotiator discovery service - provides available negotiators with filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class NegotiatorInfo:
    """Information about an available negotiator."""

    name: str
    full_path: str
    group: str
    category: str | None = None  # "winner", "finalist", or None


# Built-in negmas SAO negotiators
_BUILTIN_NEGOTIATORS = [
    "AspirationNegotiator",
    "NaiveTitForTatNegotiator",
    "SimpleTitForTatNegotiator",
    "TimeBasedConcedingNegotiator",
    "TimeBasedNegotiator",
    "BoulwareTBNegotiator",
    "ConcederTBNegotiator",
    "LinearTBNegotiator",
    "ToughNegotiator",
    "NiceNegotiator",
    "RandomNegotiator",
    "RandomAlwaysAcceptingNegotiator",
    "LimitedOutcomesNegotiator",
    "LimitedOutcomesAcceptor",
    "TopFractionNegotiator",
    "MiCRONegotiator",
    "FastMiCRONegotiator",
    "HybridNegotiator",
    "CABNegotiator",
    "CANNegotiator",
    "CARNegotiator",
    "WABNegotiator",
    "WANNegotiator",
    "WARNegotiator",
    "UtilBasedNegotiator",
    "ControlledSAONegotiator",
    "SAONegotiator",
]

# Genius agents registry - organized by ANAC year with winners/finalists info
_GENIUS_AGENTS: dict[str, dict[str, list[str]]] = {
    "basic": {
        "all": [
            "TimeDependentAgent",
            "TimeDependentAgentBoulware",
            "TimeDependentAgentConceder",
            "TimeDependentAgentLinear",
            "TimeDependentAgentHardliner",
        ],
        "winners": ["TimeDependentAgent"],
        "finalists": ["TimeDependentAgent"],
    },
    "anac2010": {
        "all": [
            "AgentK",
            "Yushu",
            "Nozomi",
            "IAMhaggler",
            "AgentFSEGA",
            "AgentSmith",
            "IAMcrazyHaggler",
        ],
        "winners": ["AgentK"],
        "finalists": ["AgentK", "Yushu", "Nozomi"],
    },
    "anac2011": {
        "all": [
            "HardHeaded",
            "Gahboninho",
            "IAMhaggler2011",
            "AgentK2",
            "BramAgent",
            "TheNegotiator",
        ],
        "winners": ["HardHeaded"],
        "finalists": ["HardHeaded", "Gahboninho", "IAMhaggler2011"],
    },
    "anac2012": {
        "all": [
            "CUHKAgent",
            "AgentLG",
            "OMACAgent",
            "TheNegotiatorReloaded",
            "MetaAgent2012",
            "IAMhaggler2012",
            "AgentMR",
        ],
        "winners": ["CUHKAgent"],
        "finalists": ["CUHKAgent", "AgentLG", "OMACAgent"],
    },
    "anac2013": {
        "all": [
            "TheFawkes",
            "MetaAgent2013",
            "TMFAgent",
            "AgentKF",
            "GAgent",
            "InoxAgent",
            "SlavaAgent",
        ],
        "winners": ["TheFawkes"],
        "finalists": ["TheFawkes", "MetaAgent2013", "TMFAgent"],
    },
    "anac2014": {
        "all": [
            "AgentM",
            "DoNA",
            "Gangster",
            "WhaleAgent",
            "TUDelftGroup2",
            "E2Agent",
            "KGAgent",
            "AgentYK",
            "BraveCat",
            "AgentQuest",
            "AgentTD",
            "AgentTRP",
            "ArisawaYaki",
            "Aster",
            "Atlas",
        ],
        "winners": ["AgentM"],
        "finalists": ["AgentM", "DoNA", "Gangster"],
    },
    "anac2015": {
        "all": [
            "Atlas3",
            "ParsAgent",
            "RandomDance",
            "AgentBuyog",
            "AgentH",
            "AgentHP",
            "AgentNeo",
            "AgentW",
            "AgentX",
            "AresParty",
            "CUHKAgent2015",
            "DrageKnight",
            "Y2015Group2",
            "JonnyBlack",
            "Kawaii",
            "MeanBot",
            "Mercury",
            "PNegotiator",
            "PhoenixParty",
            "PokerFace",
            "SENGOKU",
            "XianFaAgent",
        ],
        "winners": ["Atlas3"],
        "finalists": ["Atlas3", "ParsAgent", "RandomDance"],
    },
    "anac2016": {
        "all": [
            "Caduceus",
            "YXAgent",
            "ParsCat",
            "AgentHP2",
            "AgentLight",
            "AgentSmith2016",
            "Atlas32016",
            "ClockworkAgent",
            "Farma",
            "GrandmaAgent",
            "MaxOops",
            "MyAgent",
            "Ngent",
            "Terra",
        ],
        "winners": ["Caduceus"],
        "finalists": ["Caduceus", "YXAgent", "ParsCat"],
    },
    "anac2017": {
        "all": [
            "PonPokoAgent",
            "CaduceusDC16",
            "BetaOne",
            "AgentF",
            "AgentKN",
            "Farma2017",
            "GeneKing",
            "Gin",
            "Group3",
            "Imitator",
            "MadAgent",
            "Mamenchis",
            "Mosa",
            "ParsAgent3",
            "Rubick",
            "SimpleAgent2017",
            "TaxiBox",
        ],
        "winners": ["PonPokoAgent"],
        "finalists": ["PonPokoAgent", "CaduceusDC16", "BetaOne"],
    },
    "anac2018": {
        "all": [
            "AgreeableAgent2018",
            "MengWan",
            "Seto",
            "Agent33",
            "AgentHerb",
            "AgentNP1",
            "AteamAgent",
            "ConDAgent",
            "ExpRubick",
            "FullAgent",
            "IQSun2018",
            "PonPokoRampage",
            "Shiboy",
            "Sontag",
            "Yeela",
        ],
        "winners": ["AgreeableAgent2018"],
        "finalists": ["AgreeableAgent2018", "MengWan", "Seto"],
    },
    "anac2019": {
        "all": [
            "AgentGG",
            "KakeSoba",
            "SAGA",
            "AgentGP",
            "AgentLarry",
            "DandikAgent",
            "EAgent",
            "FSEGA2019",
            "GaravelAgent",
            "Gravity",
            "HardDealer",
            "KAgent",
            "MINF",
            "WinkyAgent",
        ],
        "winners": ["AgentGG"],
        "finalists": ["AgentGG", "KakeSoba", "SAGA"],
    },
}

# All available groups
NEGOTIATOR_GROUPS = ["builtin"] + list(_GENIUS_AGENTS.keys())


def get_negotiators(
    group: str | list[str] | None = None,
    category: Literal["all", "winners", "finalists"] = "all",
) -> list[NegotiatorInfo]:
    """
    Get available negotiators filtered by group and category.

    Args:
        group: Group(s) to filter by. Can be:
            - "builtin": Built-in negmas SAO negotiators
            - "basic": Basic time-dependent genius agents
            - "anac2010" through "anac2019": ANAC competition agents by year
            - A list of groups
            - None for all groups
        category: For genius agents, filter by competition results:
            - "all": All agents in the group
            - "winners": Only competition winners (1st place)
            - "finalists": Top 3 finishers

    Returns:
        List of NegotiatorInfo objects with name, full_path, group, and category.
    """
    if group is None:
        groups = NEGOTIATOR_GROUPS
    elif isinstance(group, str):
        groups = [group]
    else:
        groups = group

    result: list[NegotiatorInfo] = []

    for g in groups:
        if g == "builtin":
            # Built-in negmas negotiators
            for name in _BUILTIN_NEGOTIATORS:
                result.append(
                    NegotiatorInfo(
                        name=name,
                        full_path=name,  # Can be used directly
                        group="builtin",
                        category=None,
                    )
                )
        elif g in _GENIUS_AGENTS:
            # Genius agents - need "genius:" prefix
            group_data = _GENIUS_AGENTS[g]
            agents = group_data.get(category, group_data["all"])
            winners = set(group_data["winners"])
            finalists = set(group_data["finalists"])

            for name in agents:
                # Determine category for this agent
                if name in winners:
                    agent_category = "winner"
                elif name in finalists:
                    agent_category = "finalist"
                else:
                    agent_category = None

                result.append(
                    NegotiatorInfo(
                        name=name,
                        full_path=f"genius:{name}",
                        group=g,
                        category=agent_category,
                    )
                )

    return result


def get_groups() -> list[dict[str, str | int]]:
    """
    Get all available negotiator groups with metadata.

    Returns:
        List of dicts with group info: id, label, count.
    """
    groups = []

    # Built-in group
    groups.append(
        {
            "id": "builtin",
            "label": "Built-in (negmas)",
            "count": len(_BUILTIN_NEGOTIATORS),
        }
    )

    # Genius agent groups
    group_labels = {
        "basic": "Basic Time-Dependent",
        "anac2010": "ANAC 2010",
        "anac2011": "ANAC 2011",
        "anac2012": "ANAC 2012",
        "anac2013": "ANAC 2013",
        "anac2014": "ANAC 2014",
        "anac2015": "ANAC 2015",
        "anac2016": "ANAC 2016",
        "anac2017": "ANAC 2017",
        "anac2018": "ANAC 2018",
        "anac2019": "ANAC 2019",
    }

    for group_id, group_data in _GENIUS_AGENTS.items():
        groups.append(
            {
                "id": group_id,
                "label": group_labels.get(group_id, group_id),
                "count": len(group_data["all"]),
            }
        )

    return groups


def search_negotiators(
    query: str,
    group: str | list[str] | None = None,
    category: Literal["all", "winners", "finalists"] = "all",
) -> list[NegotiatorInfo]:
    """
    Search negotiators by name with optional group/category filter.

    Args:
        query: Search string (case-insensitive substring match)
        group: Optional group filter
        category: Optional category filter for genius agents

    Returns:
        List of matching NegotiatorInfo objects.
    """
    all_negotiators = get_negotiators(group=group, category=category)
    query_lower = query.lower()

    return [n for n in all_negotiators if query_lower in n.name.lower()]
