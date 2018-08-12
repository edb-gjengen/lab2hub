**lab2hub** syncs from gitlab to github like described in [this GitHub article](https://help.github.com/articles/duplicating-a-repository/#mirroring-a-repository).

## Install
    pipenv install
    cp config-example.py config.py  # Change GitHub and GitLab url and key
    pipenv shell
    python lab2hub.py

## TODO

- On gitlab webhook, per repo
- use with dedicated github org user
