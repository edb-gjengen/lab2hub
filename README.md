**lab2hub** syncs from gitlab to github like described in [this GitHub article](https://help.github.com/articles/duplicating-a-repository/#mirroring-a-repository).

## Install
    pyvenv venv
    . venv/bin/activate
    pip install -r requirements.txt

## Usage

* Create a `config.py` with GitHub and GitLab url and key.
* Use `config-example.py` as a template.
* run with `python lab2hub.py`.


## TODO

- On gitlab webhook, per repo
