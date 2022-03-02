# tt-cli, a timesheet editor for your cli
## What it is
This is a basic program meant to do one thing: write hours to timesheet
services in the cloud.

## Why?
Because sometimes (always) as a consultant they will ask you to log your hours
in more than one place, and, from the bottom of my heart, _fuck that_.

## What can it do?
Currently it can log hours to Visma Severa, Noa Workbook, and Tripletex, with
severe caveats. You do this with the bundled commands `tt-cli write-to-all 7.5
"Today I wrote all the tests"` for example puts 7.5 hours in your configured
systems with the comment "Today I wrote all the tests". You can see help
textfor any command by passing `--help`. A good starting point would be `tt-cli
--help`

## What caveats?
### Severa
* We can only log to a single project and a single phase.
* We determine the project by asking the api which are available and picking the first one
* We determine the phase in the same way
* They wouldn't give me real api access, so we use scraping techniques to login and obtain an access token

### Noa Workbook
* Will only log to the default activity, which will be your top pinned activity.
(if you use `tt-cli noa configure` it will tell you which activity it's going to use)
* Does not lock ("approve") hours for now

### Tripletex
Their API is [open source](https://github.com/tripletex/tripletex-api2/), and
they have an open test environment. That's all I've got access to, because in
order to get a consumer token and an employee token, you need to be a known
integration partner, which we are not (yet). Worse, when I created a test
environment with them, I for some reason got an environment where my one and
only user doesn't have project administration access. Thus:

* We can only log hours to non-project activities
* You need to supply your own consumer token as well as employee token

Getting an employee token is simple enough as long as you've got the rights, [ref their docs](https://tripletex.no/execute/docViewer?articleId=853&language=0),
however afaik there is no way to get a consumer token without being an integration partner.

## Ok, how do I set this up?
I recommend installing with
[pipx](https://github.com/pypa/pipx#pipx--install-and-run-python-applications-in-isolated-environments)
so as not to pollute your global python environment, however if you want you
can just install with regular pip.

```shell
$ pipx install --index-url https://pypi.brbcoffee.com/simple/ ttcli

# Or if you don't want/have pipx
$ pip install --user --index-url https://pypi.brbcoffee.com/simple/ ttcli

# Or if you just don't care
$ pip install --index-url https://pypi.brbcoffee.com/simple/ ttcli
```

You now have the following programs installed. If you used the pip method, it
may have shown some warnings about adding a directory to your PATH. Do so.
* `tt-cli` the main program
* `tt-a` a shortcut to `tt-cli write-to-all`

Next you need to set up your environment variables. There's a `.env.template`
file in this project, copy it to `.env` and fill in the blanks. To find the
tripletex activity id you may use the `tt-cli tripletex find` command. That's
it, now refer back to [usage](#what-can-it-do).
