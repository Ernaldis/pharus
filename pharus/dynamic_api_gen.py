from textwrap import indent
from pathlib import Path
import os
import yaml
import pkg_resources
import json
import re


def populate_api():
    header_template = """# Auto-generated rest api
from .server import app, protected_route
from .interface import _DJConnector, dj
from flask import request
from json import loads
from base64 import b64decode
from datetime import datetime
import inspect
import traceback
try:
    from .extra_component_interface import type_map
except (ModuleNotFoundError, ImportError):
    from .component_interface import type_map
"""
    route_template = """

@app.route('{route}', methods=['GET'])
@protected_route
def {method_name}(jwt_payload: dict) -> dict:

    if request.method in {{'GET'}}:
        try:
            component_instance = type_map['{component_type}'](name='{component_name}',
                                                              component_config={component},
                                                              jwt_payload=jwt_payload)
            return component_instance.{method_name_type}()
        except Exception as e:
            return traceback.format_exc(), 500
"""

    pharus_root = f"{pkg_resources.get_distribution('pharus').module_path}/pharus"
    api_path = f'{pharus_root}/dynamic_api.py'
    spec_path = os.environ.get('API_SPEC_PATH')

    with open(Path(api_path), 'w') as f, open(Path(spec_path), 'r') as y:
        f.write(header_template)
        values_yaml = yaml.load(y, Loader=yaml.FullLoader)
        if ('extra_components' in values_yaml['SciViz'] and
                'config' in values_yaml['SciViz']['extra_components']):
            with open(Path(pharus_root,
                           'extra_component_interface.py'), 'w') as extra_component_config:
                extra_component_config.write(
                    values_yaml['SciViz']['extra_components']['config'])

        try:
            from .extra_component_interface import type_map
        except (ModuleNotFoundError, ImportError):
            from .component_interface import type_map

        pages = values_yaml['SciViz']['pages']
        # Crawl through the yaml file for the routes in the components
        for page in pages.values():
            for grid in page['grids'].values():
                if grid['type'] == 'dynamic':
                    f.write(route_template.format(
                        route=grid['route'],
                        method_name=grid['route'].replace('/', ''),
                        component_type='table',
                        component_name='dynamicgrid',
                        component=json.dumps(grid),
                        method_name_type='dj_query_route'))

                for comp_name, comp in (grid['component_templates']
                                        if 'component_templates' in grid
                                        else grid['components']).items():
                    if re.match(r'^(table|metadata|plot).*$', comp['type']):
                        f.write(route_template.format(
                            route=comp['route'],
                            method_name=comp['route'].replace('/', ''),
                            component_type=comp['type'],
                            component_name=comp_name,
                            component=json.dumps(comp),
                            method_name_type='dj_query_route'))
                        if type_map[comp['type']].attributes_route_format:
                            attributes_route = type_map[
                                comp['type']].attributes_route_format.format(
                                    route=comp["route"])
                            f.write(route_template.format(
                                route=attributes_route,
                                method_name=attributes_route.replace('/', ''),
                                component_type=comp['type'],
                                component_name=comp_name,
                                component=json.dumps(comp),
                                method_name_type='attributes_route'))
