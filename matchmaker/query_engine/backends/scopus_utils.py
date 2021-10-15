from pybliometrics.scopus.utils.constants import DEFAULT_PATHS
from pybliometrics.scopus.utils.startup import config, CONFIG_FILE

# Edited from pybliometrics
def create_config(key, token = None):
    """Initiates process to generate configuration file."""
    #if CONFIG_FILE.exists():
    # Set directories
    if not config.has_section('Directories'):
        config.add_section('Directories')
    
    for api, path in DEFAULT_PATHS.items():
        config.set('Directories', api, str(path))
    # Set authentication
    if not config.has_section('Authentication'):
        config.add_section('Authentication')
    config.set('Authentication', 'APIKey', key)
    if token:
        config.set('Authentication', 'InstToken', token)
    # Write out
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w+") as ouf:
        config.write(ouf)
