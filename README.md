# tt-cli, a timesheet editor for your cli
## What it is
This is a basic program meant to do one thing: write hours to timesheet services in the cloud.

## Why?
Because sometimes as a consultant they will ask you to log your hours in more than one place,
and, from the bottom of my heart, _fuck that_.

## What can it do?
Currently it can log hours to Visma Severa and Tripletex, with severe caveats.
You do this with the bundled commands
`tt-cli write-to-all 7.5 "Today I wrote all the tests"` for example puts 7.5 hours in tripletex and
severa with the comment "Today I wrote all the tests".
You can see help text for any command by passing `--help`. A good starting point would be `tt-cli --help`

## What caveats?
### Severa
* We can only log to a single project and a single phase.
* We determine the project by asking the api which are available and picking the first one
* We determine the phase in the same way
* They wouldn't give me real api access, so we use scraping techniques to login and obtain an access token

### Tripletex
Their API is [open source](https://github.com/tripletex/tripletex-api2/), and they have an open test environment.
That's all I've got access to, because in order to get a consumer token and an employee token, you need to be a
known integration partner, which we are not (yet). Worse, when I created a test environment with them,
I for some reason got an environment where my one and only user doesn't have project administration access. Thus:

* We can only log hours to non-project activities
* You need to supply your own consumer token as well as employee token

Getting an employee token is simple enough as long as you've got the rights, [ref their docs](https://tripletex.no/execute/docViewer?articleId=853&language=0),
however afaik there is no way to get a consumer token without being an integration partner.

## Ok, how do I set this up?
First things first, install the dependencies with pipenv
```shell
$ pip install --user pipenv
$ pipenv install
```
This has created a python venv for you with the dependencies of this project, as well as installed two commands to that venv
* `tt-cli` the main program
* `tt-a` a shortcut to `tt-cli write-to-all`

Add the location of the venv bin folder to your path
```shell
$ echo "PATH=\$PATH:$(pipenv --venv)/bin" >> ~/.zshrc
```
or `.bashrc` or whichever shell you're on.

Next you need to set up your environment variables. There's a `.env.template` file in this project,
copy it to `.env` and fill in the blanks. To find the tripletex activity id you may use the
`tt-cli tripletex find` command. That's it, now refer back to [usage](#what-can-it-do).
