from enum import Enum
from cat.mad_hatter.decorators import plugin
from pydantic import BaseModel, Field, field_validator

# Enum class to define available voice options for the TTS plugin.
class VoiceSelect(Enum):
    Alice: str = 'Alice'
    Eve: str = 'Eve'
    Amy: str = 'Amy'
    Sonya: str = 'Sonya'
    Stephany: str = 'Stephany'
    Dave: str = 'Dave'
    Stephan: str = 'Stephan'
    Joe: str = 'Joe'
    Ruslan: str = 'Ruslan'
    Riccardo: str = 'Riccardo'
    Paola: str = 'Paola'

# Settings model to store user preferences such as selected voice.
class piperCatSettings(BaseModel):
    Voice: VoiceSelect = VoiceSelect.Paola  # Default voice is set to "Paola"


# Function that returns the schema of the settings, used by the plugin system.
@plugin
def settings_schema():
    return piperCatSettings.schema()
