import logging
import os
from collections import OrderedDict

from gitlab import Gitlab
from github3 import login
import git

# Default config
BASE_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.join(BASE_DIR, 'repos')

# Log config
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
logger.addHandler(logging.StreamHandler())


try:
    import config
except ImportError:
    pass


def get_gitlab_repo_data(gl_api, group_id):
    projects = list(filter(lambda x: x.public, gl_api.groups.get(group_id).projects))
    repos = OrderedDict()
    for project in projects:
        name = project.http_url_to_repo.split('/')[-1].split('.')[0]
        repos[name] = {
            'description': project.name,
            'clone_url': project.http_url_to_repo,
            'name': name,
        }
    return repos


def get_github_repo_data(org):
    gh_repos = list(org.repositories())
    repos = OrderedDict()

    for r in gh_repos:
        name = r.name.lower()

        repos[name] = {
            'ssh_url': r.ssh_url,
            'name': name
        }
    return repos


def git_clone(git_url, dir_name):
    local_path = os.path.join(REPO_DIR, dir_name)
    if not os.path.exists(local_path):
        logger.debug('Cloning %s into bare repo %s', git_url, local_path)
        git.Repo.clone_from(git_url, local_path, mirror=True)
    else:
        logger.debug('Fetch from %s (origin) into %s', git_url, local_path)
        r = git.Repo(local_path)
        r.remotes.origin.fetch(prune=True)


def git_push(dir_name, hub_url):
    remote_branch_name = 'github'
    local_path = os.path.join(REPO_DIR, dir_name)
    r = git.Repo(local_path)

    try:
        remote = r.remote(remote_branch_name)
    except ValueError:
        logger.debug('Created remote %s', remote_branch_name)
        remote = r.create_remote(remote_branch_name, hub_url)

    logger.debug('Pushing %s (%s) to %s', local_path, remote_branch_name, hub_url)
    remote.push(mirror=True)


def create_github_repository(gh_org, name):
    repo = gh_org.create_repository(name)
    return {
        'ssh_url': repo.ssh_url,
        'name': name
    }


def lab2hub(gl_repo, gh_repo):
    git_clone(gl_repo['clone_url'], gl_repo['name'])
    git_push(gl_repo['name'], gh_repo['ssh_url'])

if __name__ == '__main__':
    # Gitlab
    gl = Gitlab(config.GITLAB_URL, config.GITLAB_TOKEN)
    gl_repo_data = get_gitlab_repo_data(gl, config.GITLAB_GROUP_ID)
    logger.info('Found {} GitLab ({}) projects'.format(len(gl_repo_data), config.GITLAB_URL))

    # Github
    gh = login(token=config.GITHUB_TOKEN)
    gh_org = gh.organization(config.GITHUB_ORG_NAME)
    gh_repo_data = get_github_repo_data(gh_org)
    logger.info('Found {} GitHub repos'.format(len(gh_repo_data)))

    # Check if repos exist and sync
    for name, gl_repo in gl_repo_data.items():
        if name not in gh_repo_data:
            logger.info('[NEW]: {}'.format(name))
            gh_repo = create_github_repository(gh_org, name)
        else:
            gh_repo = gh_repo_data[name]

        lab2hub(gl_repo, gh_repo)
        logger.info('[OK]: {}'.format(name))
