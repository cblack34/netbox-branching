from netbox.plugins import PluginConfig


class AppConfig(PluginConfig):
    name = 'netbox_branching'
    verbose_name = 'NetBox Branching'
    description = 'A git-like branching implementation for NetBox'
    version = '0.1'
    base_url = 'branching'
    # min_version = '4.0'
    middleware = [
        'netbox_branching.middleware.BranchMiddleware'
    ]
    default_settings = {
        # This string is prefixed to the name of each new branch schema during provisioning
        'schema_prefix': 'branch_',
    }

    def ready(self):
        super().ready()
        from . import search, signals


config = AppConfig
