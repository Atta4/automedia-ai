"""
Viral Script Generator Module

Generates high-retention, viral-optimized scripts using proven frameworks.
"""

from .generator import ViralScriptGenerator
from .models import ViralScript, ScriptSegment, HookFramework, ScriptGenerationRequest
from .hook_library import HookLibrary

__all__ = [
    "ViralScriptGenerator",
    "ViralScript",
    "ScriptSegment",
    "HookFramework",
    "ScriptGenerationRequest",
    "HookLibrary",
]
