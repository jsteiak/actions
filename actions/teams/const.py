TEAMS = {"YNS": ["jsteiak"]}
MEMBERS = {
    member: team for team, members in TEAMS.items() for member in members
}

TEAM_PROJECTS = {"YNS": "istiakog"}

PROGRESS_LABELS = {
    "0 - Backlog": 0,
    "1 - Ready": 1,
    "2 - Working": 2,
    "3 - Complete": 3,
}
PROJECT_PROGRESS_COLUMNS = {
    label: label.split(" - ")[1] for label in PROGRESS_LABELS
}
PROJECT_PROGRESS_COLUMNS_ALT = {
    "1 - Ready": "To do",
    "2 - Working": "In progress",
    "3 - Complete": "Done",
}
