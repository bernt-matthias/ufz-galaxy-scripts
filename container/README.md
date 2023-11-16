
# Dependency management scripts

These scripts are currently used for the management of dependencies.
The main motivation is from the need to migrate from conda to
singularity.

Idea was to setup Galaxy such that it will use containers if one
is cached and conda otherwise. For the cached containers I intend
to use only containers from biocontainers (and explicit containers)/
With such a setup one can migrate step by step in order to avoid
side effects for users.

## Setup 

When installing tools I disabled automatic installation any resolver
dependencies, i.e. conda dependencies, but existing conda environments
are kept.

I setup the container resolvers in `galaxy.yml`` such that only
`cached_explicit_singularity`, `cached_mulled_singularity` and
`mulled_singularity` are used:

```yml
  container_resolvers:
  - type: cached_explicit_singularity
    cache_directory: /GALAXY_ROOT/database/container_cache/singularity
  - type: cached_mulled_singularity
    cache_directory: /GALAXY_ROOT/database/container_cache/singularity
  - type: mulled_singularity
    auto_install: False
    cache_directory: /GALAXY_ROOT/database/container_cache/singularity
```

The main difference to the default container resolvers is that
`build_mulled_singularity` is not used. And the `mulled_singularity` only
installs if this is explicitly triggered (e.g. via the admin UI or API).
Note that this would still also trigger the installation (caching) of
a container when running on a container enabled destination.

Therefore, for running tools I adapted the compute environments (aka destination(s))
in my `job_conf.xml` such that that they use a special container resolver
configuration with does not allow any installation of containers.

```xml
<destination id="NAME_singularity" runner="drmaa">
    ...
    <param id="singularity_enabled">true</param>
    <param id="container_resolvers_config_file">config/container_resolvers_dest.yml</param>
    ...
</destination>
```

Where `config/container_resolvers_dest.yml` has the following content (it's the
same as the main config minus the `mulled_singularity`):

```yml
- type: cached_explicit_singularity
  cache_directory: /GALAXY_ROOT/database/container_cache/singularity
- type: cached_mulled_singularity
  cache_directory: /GALAXY_ROOT/database/container_cache/singularity
```

So, for running tools the container resolvers will check for cached containers and
if none is found the destination will fall back to conda.

## Installation of new containers

The script `install_container.py` helps with the installation of new containers.
With `--include` and `--exclude` tools can be filtered by regular expressions
that are applied on the tools guid, e.g. 

- `--include '/iuc/'` include all toos owned by IUC
- `--exclude 'testtoolshed'` exclude tools from the testtoolshed

Additionally with `--latest` only the latest version of the tool is considered.
By default the tool makes a dry run. Containers are only installed with `--install_container`.

Over time added more and more `--include` directives, at the moment I have daily cron
jobs with the following setup:

```bash
python install_container.py --latest --url GALAXY_URL --key API_KEY --install_container 
    --include '^(?!toolshed\\.g2\\.bx\\.psu\\.edu).*' --exclude 'testtoolshed' 
    --include '/bgruening/' --include '/devteam/' --include '/earlhaminst/' --include '/galaxyp/'
    --include '/imgteam/' --include '/iuc/' --include '/lparsons/' --include '/rnateam/'
    --include '/yating-l/' --include '/computational-metabolomics/' &&
python install_container.py --latest --url GALAXY_URL --key API_KEY --install_container
    --include '^(?!toolshed\\.g2\\.bx\\.psu\\.edu).*'
    --exclude 'testtoolshed'
    --include '/workflow4metabolomics/' --include '/lecorguille/' --include '/mmonsoor/'
    --include '/prog/' --include '/marie-tremblay-metatoul/' --include '/yguitton/'
    --include '/melpetera/' --include '/eschen42/' --include '/fgiacomoni/'
    --include '/ethevenot/'
```

## Removal of unused conda environments

By successively caching containers some conda environments become unneeded.
The script `deps_w_container.py` checks for conda environments used by a set of
tools whose dependencies are also available as cached containers, i.e. conda
environments that are not used anymore. Note that conda environments are only removed
if `--remove` is given.

`unused_deps.py` removes conda environments that are not used at all.

In addition `check.py` checks for tools whose requirements are not fulfilled by
a conda environment or a cached container.

I run a weekly cron job with the following setup.

```bash
python deps_w_container.py --url GALAXY_URL --key API_KEY --remove
python unused_deps.py --url GALAXY_URL --key API_KEY --remove &&
python check.py --url GALAXY_URL --key API_KEY
```