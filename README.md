# tt-cli, a timesheet editor for your cli
## What it is
This is a basic program meant to do one thing: write hours to timesheet
services in the cloud.

## Why?
Because sometimes (always) as a consultant they will ask you to log your hours
in more than one place, and, from the bottom of my heart, _no_.

## Installation and setup
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

Next you need to login to your services. Check `tt-cli configure` for a list.  
That's it, now refer back to [usage](#what-can-it-do).

### Extra notes on configuring TripleTex

#### Service url
TripleTex needs an external auth broker to be configured. When you run `tt-cli configure tripletex`
you will be prompted for your employee token and a service url. The service url will
be the auth broker. This needs to be a full url, like "https://example.com/login" _including the `/login` part_.
Ask whoever configured the broker in your organization for the url and just paste it directly.

#### Employee token
See (this link)[https://hjelp.tripletex.no/hc/no/articles/4409557117713-API-Opprette-brukern%C3%B8kkel-Integrasjon-for-sluttbruker-og-regnskapsf%C3%B8rer]
Ask whoever configured the integration for which name to put in the application name field as this is important.
Select the option for giving the token the same rights as the current user.

You can alawys rotate the generated token, so just make sure you copy it before clicking ok once TripleTex has generated it.


## What can it do?
Currently it can log hours to Visma Severa, Noa Workbook, and Tripletex, with
some caveats. You do this with the bundled commands, so `tt-cli write-to-all 7.5
"Today I wrote all the tests"` for example puts 7.5 hours in your configured
systems with the comment "Today I wrote all the tests". You can see help text
for any command by passing `--help`. A good starting point would be `tt-cli
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
You will need to get TripleTex to create an app and a consumer token for you in order to log hours
against production. There's a step-by-step guide [here](https://developer.tripletex.no/getting-started/).
Once they have created your app your employees will need to generate their own employee tokens.
They have some docs for this [in norwegian](https://hjelp.tripletex.no/hc/no/articles/4409557117713-API-Opprette-brukern%C3%B8kkel-Integrasjon-for-sluttbruker-og-regnskapsf%C3%B8rer)

## Requirements
### Python ^3.10
This project uses PEP 612, because it's amazing, and therefore it needs python
3.10 or greater. If your system doesn't have python 3.10, I recommend looking into
[asdf](https://asdf-vm.com/) or [pyenv](https://github.com/pyenv/pyenv) to work
around aging os distributions.

### Keyring
To keep you from having to log in every time you use the app, we store your
credentials. To store the credentials securely, we use the OS keyring to store
an encryption key. If you don't have a keyring set up that probably means
you're on some custom linux system you've built yourself. First of all: nice!
Second of all: I can't possibly help with every single toaster running arch,
but you could start looking [here](https://pypi.org/project/keyring/).

### Running the TripleTex auth service
The auth service is packaged into a docker image, and just needs to know which
consumer token to use and whether to target tripletex testing or prod.
Optionally you may also pass a port to run the service on. Default is 8000.

```bash
$ docker run \
    -e TT_CONSUMER_TOKEN=<your-app-consumer-token> \
    -e TT_PROD=true \
    -e TT_AUTH_PORT=<port-number> \
    ghcr.io/bjornsnoen/tt-cli:auth
```
