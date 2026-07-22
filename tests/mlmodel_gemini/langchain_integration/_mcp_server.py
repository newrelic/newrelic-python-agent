# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mcp.server.fastmcp import FastMCP


# Define MCP Server
server = FastMCP("DH")

@server.tool()
def add_exclamation(phrase: str):
    """ 
    Add an exclamation point to the end of the phrase.
    """
    return f"{phrase}!"

@server.tool()
def capitalize_message(phrase: str):
    """ 
    Capitalize the letters within the phrase.
    """
    return f"{phrase.upper()}"


server.run(transport="stdio")
