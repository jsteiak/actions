TEAMS = {"YNS": ["jsteiak"]}
MEMBERS = {
    member: team for team, members in TEAMS.items() for member in members
}

TEAM_PROJECTS = {"istiakog": "YNS"}

PROGRESS_LABELS = {
    "0 - Backlog": 0,
    "1 - Ready": 1,
    "2 - Working": 2,
    "3 - Complete": 3,
}
PROJECT_COLUMNS = {label: label.split(" - ")[1] for label in PROGRESS_LABELS}
