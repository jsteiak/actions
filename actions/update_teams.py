from json import loads, dumps
from os import getenv
from requests import get as http_get, post as http_post
from urllib.parse import urlencode

GITHUB_TOKEN = getenv('GITHUB_TOKEN')

AUTHORIZATION_HEADER = f'token {GITHUB_TOKEN}'
ISSUES_ACCEPT_HEADER = 'application/vnd.github.v3.full+json'
PROJECTS_ACCEPT_HEADER = 'application/vnd.github.inertia-preview+json'

ISSUE_HEADERS = {
    'accept': ISSUES_ACCEPT_HEADER,
    'authorization': AUTHORIZATION_HEADER
}

PROJECT_HEADERS = {
    'accept': PROJECTS_ACCEPT_HEADER,
    'authorization': AUTHORIZATION_HEADER
}


ORG = 'obsrvbl'
ISSUES_REPOS = ["devops",
                #   "cspm-issues",
                ]

ORG_URL = f"https://api.github.com/orgs/{ORG}"
ISSUES_REPOS_URL = [
    f"https://api.github.com/repos/{ORG}/{issue_repo}" for issue_repo in ISSUES_REPOS]

TEAMS = {
    'BAS': ['bastamper', 'mcneo', 'jmuskovitz', 'silchencko', 'wesley-smith'],
    #     'BMB': ['bbayles', 'mrg29', 'mkiselyow', 'MayCisco', 'tpeaton', 'qaispak', 'VladyslavKhanin'],
    'MJS': ['mjschultz', 'snycewerk', 'yuriibruzha', 'ygavenchuk', 'ohrinish', 'vkozelsk', 'denyskulykov', 'nposlovska'],
    'JPM': ['jmarkey', 'Ostaijen', 'mpanaro-cisco', 'milesoldenburg', 'vicawork'],
    'YNS': ['jsteiak', 'tacshooter', 'jchapian', 'alerkasun', 'jcraiggoodell', 'swc-karim'],
}

TEAM_PROJECTS_URL = {
    'BAS': 'https://api.github.com/projects/6032435',
    'MJS': 'https://api.github.com/projects/5919023',
    'JPM': 'https://api.github.com/projects/6032546',
    'YNS': 'https://api.github.com/projects/6032560',
}

PROGRESS_LABELS = {
    '0 - Backlog': 0,
    '1 - Ready': 1,
    '2 - Working': 2,
    '3 - Complete': 3,
}
PROJECT_COLUMNS = {l: l.split(' - ')[1] for l in PROGRESS_LABELS}


def http_get_paging(url, headers):
    while url:
        resp = http_get(url, headers=headers)
        yield from resp.json()
        url = resp.links.get("next", {}).get('url')
    return


def get_progress_label(labels):
    max_progress = -1
    progress_label = None
    for label in labels:
        name = label['name']
        progress = PROGRESS_LABELS.get(name, -1)
        if progress > max_progress:
            max_progress = progress
            progress_label = name

    return progress_label


def get_project_info():
    project_headers = {
        'accept': PROJECTS_ACCEPT_HEADER,
        'authorization': AUTHORIZATION_HEADER
    }

    columns = {}
    cards = {}

    for team in TEAMS:
        project_url = TEAM_PROJECTS_URL.get(team)
        if not project_url:
            continue

        project = http_get(project_url, headers=project_headers).json()
        for column in http_get_paging(project.get('columns_url'), headers=project_headers):
            columns[(team, column["name"])] = {
                "url": column['url'],
                "id": column['id'],
            }
            card_url = column.get('cards_url')
            for card in http_get_paging(card_url, headers=project_headers):
                content_url = card.get('content_url')
                if not content_url:
                    continue
                issue_nr = int(card.get('content_url').split('/')[-1])
                cards[(team, issue_nr)] = {
                    "url": card['url'],
                    "column": column["name"],
                }

    return columns, cards


def get_issue_info():
    query_params = {'state': 'open', 'assignee': '*'}

    issues = {}
    for team in TEAMS:
        for member in TEAMS[team]:
            query_params['assignee'] = member
            for issues_repo_url in ISSUES_REPOS_URL:
                url = f'{issues_repo_url}/issues?{urlencode(query_params)}'
                for issue in http_get_paging(url, headers=ISSUE_HEADERS):
                    issue_nr = issue['number']
                    progress_label = get_progress_label(issue['labels'])
                    issues[(team, issue_nr)] = {
                        "url": issue['url'],
                        "html_url": issue['html_url'],
                        "id": issue['id'],
                        "column": PROJECT_COLUMNS.get(progress_label)
                    }
    return issues


def fix_mismatches(columns, cards, issues):
    for (team, issue_nr), issue_info in issues.items():
        card_info = cards.get((team, issue_nr))

        if not card_info:
            print(f"{issue_info['html_url']} not found in {team}.")
            column_url = columns.get((team, issue_info['column']), {}).get('url')
            if not column_url:
                print("[ERROR] Column URL not found.")
                continue
            url = f"{column_url}/cards"
            data = dumps({'content_id': issue_info['id'], 'content_type': 'Issue'})
            resp = http_post(url, headers=PROJECT_HEADERS, data=data)
            resp.raise_for_status()
            print(f"Assigned {issue_info['html_url']} to {team}.")
            continue

        if issue_info['column'] != card_info['column']:
            print(
                f"{issue_info['html_url']} is {issue_info['column']} but appears as {card_info['column']} in {team}.")

            column_id = columns.get((team, issue_info['column']), {}).get('id')
            if not column_id:
                print("[ERROR] Column ID not found.")
                continue
            url = f"{card_info['url']}/moves"
            data = dumps({'column_id': column_id, 'position': 'top'})
            resp = http_post(url, headers=PROJECT_HEADERS, data=data)
            resp.raise_for_status()
            print(f"Moved {issue_info['html_url']} to {card_info['column']} in {team}.")


def main():
    columns, cards = get_project_info()
    issues = get_issue_info()
    fix_mismatches(columns, cards, issues)

    return 0


def test_main():
    context = loads(getenv("GITHUB_CONTEXT"))
    action = context.get("action")
    label = context.get("label", {}).get("name")
    print(action, label)

    return 0


if __name__ == '__main__':
    print(getenv("GITHUB_CONTEXT"))
    exit(test_main())
