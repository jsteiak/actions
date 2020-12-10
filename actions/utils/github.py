from os import getenv
import requests

GITHUB_TOKEN = getenv("GITHUB_TOKEN")
ISSUE_HEADERS = {
    "accept": "application/vnd.github.v3.full+json",
    "authorization": f"token {GITHUB_TOKEN}",
}
PROJECT_HEADERS = {
    "accept": "application/vnd.github.inertia-preview+json",
    "authorization": f"token {GITHUB_TOKEN}",
}


def http_get(url, **kwags):
    resp = requests.get(url, **kwags)
    resp.raise_for_status()
    return resp.json()


def http_list(url, **kwags):
    while url:
        resp = requests.get(url, **kwags)
        resp.raise_for_status()
        yield from resp.json()
        url = resp.links.get("next", {}).get("url")
    return


def http_post(url, **kwags):
    resp = requests.post(url, **kwags)
    resp.raise_for_status()
    return resp.json()
