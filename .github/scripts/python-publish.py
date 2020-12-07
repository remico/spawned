#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  This file is part of "Spawned" project
#
#  Author: Roman Gladyshev <remicollab@gmail.com>
#  License: GNU Lesser General Public License v3.0 or later
#
#  SPDX-License-Identifier: LGPL-3.0+
#  License text is available in the LICENSE file and online:
#  http://www.gnu.org/licenses/lgpl-3.0-standalone.html
#
#  Copyright (c) 2020 remico

import requests
import string
from os import getenv
from pathlib import Path
from requests.auth import HTTPBasicAuth


api_server = getenv('GITHUB_API_URL')
repo_server = getenv('GITHUB_SERVER_URL')
repo = getenv('REPO')  # owner/repo pair
repo_owner = repo.split('/')[0]
repo_name = repo.split('/')[1]
repo_pass = getenv('PYPI_PASS')

tpl_page = string.Template(f"""\
<!DOCTYPE html>
<html>
<head>
  <title>{repo_name}</title>
</head>
<body>
  <!-- <a href="git+https://github.com/remico/{repo_name}.git@develop#egg={repo_name}-1!0.dev0" data-requires-python="&gt;=3.8">{repo_name}-develop</a> -->
  <a href="git+https://github.com/remico/{repo_name}.git@master#egg={repo_name}-1!0a" data-requires-python="&gt;=3.8">{repo_name}-0</a>
  <!-- <a href="{repo_name}-2020.8.11.dev1417-cp38-cp38-linux_x86_64.whl" data-requires-python="&gt;=3.8">{repo_name}</a> -->
  $releases
</body>
</html>
""")

tpl_release = string.Template(f"""\
<a href="git+https://github.com/remico/{repo_name}.git@$version#egg={repo_name}-$version" data-requires-python="&gt;=3.8">{repo_name}-$version</a>
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
Path(f"pypi/{repo_name}/index.html").write_text(html_page)

print("GITHUB_REF:", getenv('GITHUB_REF'))
set_output("READY_TO_PUSH", True)
