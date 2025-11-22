import inspect
import importlib
from pathlib import Path
from typing import Callable, List
from .base_tool import LLMTool
from .base_tool_repository import ToolRepository


def _discover_tool_functions(module) -> List[Callable]:
    """
    Discover all callable functions in a module that should be converted to tools.
    Excludes private functions (starting with _) and imported functions.
    """
    functions = []
    module_name = module.__name__
    
    for name, obj in inspect.getmembers(module):
        # Only include callable functions that are defined in this module
        if (inspect.isfunction(obj) and 
            not name.startswith('_') and
            obj.__module__ == module_name):
            functions.append(obj)
    
    return functions


def _load_tools_from_module(module_name: str) -> List[LLMTool]:
    """
    Load all tools from a module by importing it and converting functions to LLMTool instances.
    
    Args:
        module_name: The full module name (e.g., 'src.tools.decition_making_tools')
        
    Returns:
        List of LLMTool instances
    """
    try:
        module = importlib.import_module(module_name)
        functions = _discover_tool_functions(module)
        return [LLMTool.from_function(func) for func in functions]
    except ImportError as e:
        # Silently skip modules that can't be imported
        return []


def _auto_discover_tool_modules() -> List[str]:
    """
    Automatically discover all tool modules in the tools directory.
    Looks for files matching *_tools.py pattern.
    
    Returns:
        List of module names (e.g., ['src.tools.decition_making_tools'])
    """
    tools_dir = Path(__file__).parent
    module_base = __package__ or 'src.tools'
    tool_modules = []
    
    for file_path in tools_dir.glob('*_tools.py'):
        module_name = f"{module_base}.{file_path.stem}"
        tool_modules.append(module_name)
    
    return tool_modules


def create_repository_with_all_tools() -> ToolRepository:
    """
    Create a ToolRepository and automatically load all tools from tool files.
    
    Returns:
        ToolRepository instance with all discovered tools registered
    """
    repository = ToolRepository()
    
    # Discover and load all tool modules
    tool_modules = _auto_discover_tool_modules()
    
    for module_name in tool_modules:
        tools = _load_tools_from_module(module_name)
        repository.register_many(module_name.split('.')[-1].replace('_tools', ''), tools)
    
    return repository


# Create the default repository with all tools automatically loaded
tool_repository = create_repository_with_all_tools()

# Export commonly used items
__all__ = [
    "LLMTool",
    "ToolRepository", 
    "tool_repository",
    "create_repository_with_all_tools",
]
