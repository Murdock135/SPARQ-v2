"""
Settings.py

This module implements app configuration. Specifically, it provides the following features:
1. Path specifications: Defines paths for configuration files, environment variables, data input and data output directories.
2. Environment variable loading: Loads environment variables from a specified .env file.
3. Configuration building: Builds a configuration object.

The key utility of this module is the configuration building. It solves the following problem.
There are a few sources of configuration (1) Configurables within the code, provided by the authors 
of this project (2) Configurables that developers can override and (3) Configurables that 
users can override. The problem is merging these different sources of configuration in a coherent and predictable manner.

It solves the problem by building the configuration in the following sequence-
load from inner config file (authors) -> load from outer config file (developers) -> load from external config file (users)

where the subsequent sources of configuration do not override the previous ones unless explicitly specified.
"""

from pathlib import Path

from pydantic_settings import BaseSettings

