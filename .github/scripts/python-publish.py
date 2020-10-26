#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  This file is part of "Spawned" project
#
#  Copyright (c) 2020, REMICO
#
#  The software is provided "as is", without warranty of any kind, express or
#  implied, including but not limited to the warranties of merchantability,
#  fitness for a particular purpose and non-infringement. In no event shall the
#  authors or copyright holders be liable for any claim, damages or other
#  liability, whether in an action of contract, tort or otherwise, arising from,
#  out of or in connection with the software or the use or other dealings in the
#  software.

__author__ = "Roman Gladyshev"
__email__ = "remicollab@gmail.com"
__copyright__ = "Copyright (c) 2020, REMICO"
__license__ = "LGPLv3+"

import requests
import string
from os import getenv
from pathlib import Path
from requests.auth import HTTPBasicAuth


tpl_page = string.Template("""\
<!DOCTYPE html>
<html>
<head>
  <title>spawned</title>
</head>
<body>
  <!-- <a href="git+https://github.com/remico/spawned.git@develop#egg=spawned-1!0.dev0" data-requires-python="&gt;=3.8">spawned-develop</a> -->
  <a href="git+https://github.com/remico/spawned.git@master#egg=spawned-1!0a" data-requires-python="&gt;=3.8">spawned-0</a>
  <!-- <a href="spawned-2020.8.11.dev1417-cp38-cp38-linux_x86_64.whl" data-requires-python="&gt;=3.8">spawned</a> -->
  $releases
</body>
</html>
""")

tpl_release = string.Template("""\
<a href="git+https://github.com/remico/spawned.git@$version#egg=spawned-$version" data-requires-python="&gt;=3.8">spawned-$version</a>
""")


# usage: ${{ steps.<step-id>.outputs.<key> }}
def set_output(key, val):
    print(f"::set-output name={key}::{val}")


# usage: according to the shell type (e.g. in bash - $KEY)
def set_output_env(key, val):
    with open(getenv('GITHUB_ENV'), "a") as env_file:
        print(f"{key}={val}", file=env_file)


# usage: according to the shell type (e.g. in bash - $KEY)
def set_output_env_multi(key, lines, delimiter='EOF'):
    with open(getenv('GITHUB_ENV'), "a") as env_file:
        print(f"{key}<<{delimiter}\n{lines}\n{delimiter}", file=env_file)


api_server = getenv('GITHUB_API_URL')
repo_server = getenv('GITHUB_SERVER_URL')
repo = getenv('REPO')  # owner/repo pair
repo_owner = repo.split('/')[0]
repo_name = repo.split('/')[1]
repo_pass = getenv('PYPI_PASS')

manual_run_for_develop = 'true' == getenv('manual_run_for_develop', False).lower()

s = requests.Session()

# get repo owner's email
api_url = f"{api_server}/users/{repo_owner}"
user_json = s.get(api_url, auth=HTTPBasicAuth(repo_owner, repo_pass)).json()
set_output_env("REPO_OWNER_EMAIL", user_json['email'])

# get releases in json format using REST API
api_url = f"{api_server}/repos/{repo}/releases"
releases_json = s.get(api_url).json()

# find release versions
releases = [release['tag_name'] for release in releases_json]
print("\nFound releases:")
print(releases)

# create index file
release_entries = [tpl_release.substitute(version=release) for release in releases]
releases_block = ''.join(release_entries).strip()
html_page = tpl_page.substitute(releases=releases_block)
Path("pypi/spawned/index.html").write_text(html_page)

print("GITHUB_REF:", getenv('GITHUB_REF'))
set_output("READY_TO_PUSH", True)
