from cat.mad_hatter.decorators import hook, plugin
from cat.log import log
from pydantic import BaseModel  # Pydantic model for validating plugin settings schema
from enum import Enum           # Enum class to define available voice options for the TTS plugin
from datetime import datetime   # Used to generate unique timestamps for audio filenames
from threading import Thread    # Allows running the TTS process in a separate thread to avoid blocking the main application flow

import subprocess  # Executes shell commands for running the Piper TTS engine
import re          # Provides regular expression operations for text cleaning and pattern matching
import os          # Handles file and directory operations, such as checking if a folder exists or creating one







# Function to check if the input text contains any Cyrillic characters.
def has_cyrillic(text):
    cyrillic_pattern = re.compile('[\u0400-\u04FF]+')
    
    return bool(cyrillic_pattern.search(text))


# Function to remove special characters from the input text while preserving basic punctuation and letters.
def remove_special_characters(text):
    pattern = r'[^a-zA-Z0-9\s.,!?\'"а-яА-ЯÀ-ÿÄäÖöÜüß]'
    clean_text = re.sub(pattern, '', text)
    
    return clean_text


# Function to check and update available voices using Piper TTS engine command-line tool.
def check_and_update_voices():
    file_path = '/app/voices.json'
    if not os.path.exists(file_path):
        try:
            # Run the Piper command to update voices
            result = subprocess.run(
                ["piper", "--update-voices", "-m", "en_US-ryan-high"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout = result.stdout.decode('utf-8', errors='replace')
            stderr = result.stderr.decode('utf-8', errors='replace')
            log.warning("Voices update completed successfully")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('utf-8', errors='replace')
            log.error(f"An error occurred while updating voices: {stderr}")
        except Exception as e:
            log.error(f"An unexpected error occurred: {e}")


# Function to run the Piper TTS process in a separate thread to avoid blocking the main execution flow.
def run_piper_process(command, output_filename, cleaned_text, cat):
    check_and_update_voices()
    
    # Extend the base command with output file details
    full_command = command + ["--output-file", output_filename]
    
    try:
        # Execute the Piper TTS command with cleaned text as input
        subprocess.run(
            full_command,
            check=True,
            input=cleaned_text.encode(),  
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        log.error(f"Error during command execution: {e}")
        log.error(f"Error output: {e.stderr.decode()}")
        return
    
    # Prepare HTML5 audio player to be sent via WebSocket for playback
    piper_audio_player = f"<audio controls autoplay><source src='{output_filename}' type='audio/wav'>Your browser does not support the audio tag.</audio>"
    cat.send_ws_message(content=piper_audio_player, msg_type='chat')


# Function to build the Piper TTS command based on user-selected voice and input text.
def build_piper_command(llm_message: str, cat):

    # Remove special characters from the input text for better compatibility with TTS engine
    cleaned_text = remove_special_characters(llm_message)
    piper_cmd = ["piper"]

    # Load user-defined settings (voice selection) from the plugin configuration
    settings = cat.mad_hatter.get_plugin().load_settings()
    selected_voice = settings.get("Voice")

    # Fallback to default voice ("Paola") if the selected voice is invalid or unsupported
    if selected_voice not in ["Alice", "Dave", "Ruslan", "Eve", "Amy", "Stephany", "Stephan", "Joe", "Sonya", "Riccardo", "Valeria", "Paola"]:
        selected_voice = "Paola"
    
    # Automatically switch to Russian voice if Cyrillic characters are detected in the input text
    if has_cyrillic(llm_message):
        selected_voice = "Ruslan"

    # Map each voice to its corresponding Piper model and optional speaker ID
    voice_mapping = {
        "Alice": ("en_US-lessac-high", None),
        "Dave": ("en_US-ryan-high", None),
        "Ruslan": ("ru_RU-ruslan-medium", None),
        "Eve": ("en_GB-vctk-medium", "99"),
        "Amy": ("en_US-amy-medium", None),
        "Stephany": ("en_US-hfc_female-medium", None),
        "Stephan": ("en_US-hfc_male-medium", None),
        "Joe": ("en_US-joe-medium", None),
        "Sonya": ("en_US-ljspeech-medium", None),
        "Riccardo": ("it_IT-riccardo-x_low", None),
        "Paola": ("it_IT-paola-medium", None),
    }

    # Retrieve the appropriate model and speaker ID based on the selected voice
    voice_cmd, speaker_cmd = voice_mapping.get(selected_voice, ("en_US-ryan-high", None))

    # Add the model to the Piper command
    piper_cmd.extend(["--model", voice_cmd])

    # If a speaker ID is required, add it to the command
    if speaker_cmd is not None:
        piper_cmd.extend(["-s", speaker_cmd])

    # Return the final command and cleaned text to be processed
    return piper_cmd, cleaned_text


# Hook function triggered before the Cat sends a message. It handles the TTS generation in a separate thread.
@hook
def before_cat_sends_message(final_output, cat):
    # Generate unique filename for the audio file using current date and time
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y%m%d_%H%M%S")
    folder_path = "/admin/assets/voice"

    # Ensure the target directory exists; create it if necessary
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Define the output file path
    output_filename = os.path.join(folder_path, f"voice_{formatted_datetime}.wav")

    # Extract the message content to be converted into speech
    message = final_output.content

    # Build the Piper TTS command based on user settings and cleaned text
    settings = cat.mad_hatter.get_plugin().load_settings()

    command, cleaned_text = build_piper_command(message, cat)

    # Run the TTS process in a separate thread to avoid blocking the main application flow
    piper_thread = Thread(
        target=run_piper_process, 
        args=(command, output_filename, cleaned_text, cat)
    )
    piper_thread.start()

    # Return the original output so the chat can proceed normally
    return final_output
