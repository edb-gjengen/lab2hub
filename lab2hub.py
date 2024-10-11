import logging
import os
from argparse import ArgumentParser
from collections import OrderedDict

import git
from dotenv import load_dotenv
from github3 import login
from gitlab import Gitlab

BASE_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.join(BASE_DIR, "repos")

# Log config
logger = logging.getLogger(__name__)
logger.setLevel("INFO")
logger.addHandler(logging.StreamHandler())

load_dotenv()

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def git_clone(git_url, dir_name):
    local_path = os.path.join(REPO_DIR, dir_name)
    if not os.path.exists(local_path):
        logger.debug("Cloning %s into bare repo %s", git_url, local_path)
        git.Repo.clone_from(git_url, local_path, mirror=True)
    else:
        logger.debug("Fetch from %s (origin) into %s", git_url, local_path)
        r = git.Repo(local_path)
        r.remotes.origin.fetch(prune=True)


def git_push(dir_name, hub_url):
    remote_branch_name = "github"
    local_path = os.path.join(REPO_DIR, dir_name)
    r = git.Repo(local_path)

    try:
        remote = r.remote(remote_branch_name)
    except ValueError:
        logger.debug("Created remote %s", remote_branch_name)
        remote = r.create_remote(remote_branch_name, hub_url)

    logger.debug("Pushing %s (%s) to %s", local_path, remote_branch_name, hub_url)
    remote.push(mirror=True)


def lab2hub(gl_repo, gh_repo):
    git_clone(gl_repo["clone_url"], gl_repo["name"])
    git_push(gl_repo["name"], gh_repo["ssh_url"])


class Lab2Hub:
    def __init__(self, gitlab_url, gitlab_group_id, github_org_name, dry_run=False):
        self.dry_run = dry_run
        self.gitlab_group_id = gitlab_group_id
        self.gitlab_url = gitlab_url

        self.gl_api = Gitlab(gitlab_url, GITLAB_TOKEN)
        self.gh_api = login(token=GITHUB_TOKEN)
        self.gh_org = self.gh_api.organization(github_org_name)

    def get_gitlab_repo_data(self):
        projects = self.gl_api.groups.get(self.gitlab_group_id).projects.list(visibility="public", all=True)
        repos = OrderedDict()
        for project in projects:
            name = project.http_url_to_repo.split("/")[-1].split(".")[0]
            repos[name] = {
                "description": project.name,
                "clone_url": project.http_url_to_repo,
                "name": name,
            }
        return repos

    def get_github_repo_data(self):
        gh_repos = list(self.gh_org.repositories())
        repos = OrderedDict()

        for r in gh_repos:
            name = r.name.lower()

            repos[name] = {"ssh_url": r.ssh_url, "name": name, "archived": r.archived}
        return repos

    def create_github_repository(self, name):
        repo = self.gh_org.create_repository(name)
        return {"ssh_url": repo.ssh_url, "name": name}

    def sync(self):
        gl_repo_data = self.get_gitlab_repo_data()
        logger.info("Found {} GitLab ({}) projects".format(len(gl_repo_data), self.gitlab_url))

        gh_repo_data = self.get_github_repo_data()
        logger.info("Found {} GitHub repos".format(len(gh_repo_data)))

        if self.dry_run:
            return

        # Check if repos exist and sync
        for name, gl_repo in gl_repo_data.items():
            if name not in gh_repo_data:
                logger.info("[NEW]: {}".format(name))
                gh_repo = self.create_github_repository(name)
            else:
                gh_repo = gh_repo_data[name]

                if gh_repo["archived"]:
                    continue

            lab2hub(gl_repo, gh_repo)
            logger.info("[OK]: {}".format(name))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--gitlab-url", default="https://git.neuf.no")
    parser.add_argument("--gitlab-group-id", default=5, type=int)
    parser.add_argument("--github-org-name", default="edb-gjengen")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    l2h = Lab2Hub(args.gitlab_url, args.gitlab_group_id, args.github_org_name, dry_run=args.dry_run)
    l2h.sync()
