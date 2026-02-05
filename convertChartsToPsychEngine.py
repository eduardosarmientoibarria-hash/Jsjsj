import json
import os
from collections import defaultdict
from pathlib import Path
from tkinter import Tk,filedialog,simpledialog,messagebox
# Crear carpeta convertChart si no existe
output_folder = Path(__file__).parent / "convertCharts"
output_folder.mkdir(exist_ok=True)
# Pedir al usuario elegir archivo JSON
Tk().withdraw()
input_file_path = filedialog.askopenfilename(
    title="Selecciona un chart JSON",
    filetypes=[("JSON files","*.json")])
if not input_file_path:
    print("No se seleccionó ningún archivo.")
    exit()
with open(input_file_path,'r',encoding='utf-8') as f:
    input_json = json.load(f)
# Selecciona el tipo de chart
chart_type = simpledialog.askstring(
    "Tipo de Chart a Psych Engine",
    "Ingresa el tipo de chart (codename / vslice):").lower()
# Pedir metadatos extras
extra_meta = {}
if chart_type in ['codename','vslice']:
    extra_meta['bpm'] = simpledialog.askinteger("BPM","BPM:",initialvalue=150)
    extra_meta['song'] = simpledialog.askstring("Song Name","Nombre de la canción:",initialvalue="Converted Song")
    extra_meta['player1'] = simpledialog.askstring("Player 1","Jugador 1:",initialvalue="bf")
    extra_meta['player2'] = simpledialog.askstring("Player 2","Jugador 2:",initialvalue="dad")
    extra_meta['gfVersion'] = simpledialog.askstring("GF Version","Versión GF:",initialvalue="gf")
    extra_meta['stage'] = simpledialog.askstring("Stage","Escenario:",initialvalue="stage")
    extra_meta['arrowSkin'] = simpledialog.askstring("Arrow Skin","Skin de flechas:",initialvalue="NOTE_assets")
    extra_meta['splashSkin'] = simpledialog.askstring("Splash Skin","Skin de splashes:",initialvalue="noteSplashes")
# preguntar dificultad V-Slice
vslice_diff = None
if chart_type == "vslice":
    vslice_diff = simpledialog.askstring(
        "Ingresa la dificultad de tu archivo",
        "¿Cómo se llama la dificultad deseas importar? \n por defecto existen: (normal, easy, hard) o sino \n una dificultad que tengas personalizada con un \n nombre propio, ingresa una dificultad existente:",
        initialvalue="normal").lower()
# CodeName Engine
def convert_codename_chart(data,meta):
    # Diccionario para agrupar por tiempo
    events_dict = defaultdict(list)
    note_types = data.get("noteTypes",[])
    output = {
        "song": {
            "player1": meta["player1"],
            "player2": meta["player2"],
            "gfVersion": meta["gfVersion"],
            "stage": meta["stage"],
            "events": [],
            "notes": [],
            "song": meta["song"],
            "bpm": meta["bpm"],
            "needsVoices": True,
            "validScore": True,
            "speed": data.get("scrollSpeed"),
            "arrowSkin": meta["arrowSkin"],
            "splashSkin": meta["splashSkin"]
        }
    }
    all_notes = []
    for strumLine in data.get("strumLines",[]):
        for note in strumLine.get("notes",[]):
            note_id = note["id"]
            if strumLine.get("position") in ["dad","girlfriend"]:
                note_id += 4
            psych_note = [note["time"],note_id,note.get("sLen",0)]
            if strumLine.get("position") == "girlfriend":
                psych_note.append("GF Sing")
            elif note.get("type",0) > 0 and note_types and note_types[note["type"]-1]:
                psych_note.append(note_types[note["type"]-1])
            all_notes.append(psych_note)
    all_notes.sort(key=lambda n: n[0])
    bpm_events = sorted(
        [{"time": ev["time"],"bpm": ev["params"][0]}
         for ev in data.get("events",[])
         if ev.get("name") == "BPM Change" and ev.get("params")],
        key=lambda e: e["time"]
    )
    last_note_time = all_notes[-1][0] if all_notes else 0
    sections = []
    note_index = 0
    current_time = 0
    current_bpm = meta["bpm"]
    section_length = (60000 / current_bpm) * 4
    bpm_event_index = 0
    change_bpm = False
    while current_time <= last_note_time:
        if bpm_event_index < len(bpm_events) and bpm_events[bpm_event_index]["time"] <= current_time:
            current_bpm = bpm_events[bpm_event_index]["bpm"]
            section_length = (60000 / current_bpm) * 4
            change_bpm = True
            bpm_event_index += 1
        current_section = []
        while note_index < len(all_notes) and all_notes[note_index][0] < current_time + section_length:
            current_section.append(all_notes[note_index])
            note_index += 1
        sections.append({
            "typeOfSection": 0,
            "sectionBeats": 4,
            "altAnim": False,
            "gfSection": False,
            "sectionNotes": current_section,
            "mustHitSection": True,
            "changeBPM": change_bpm,
            "bpm": current_bpm
        })
        current_time += section_length
    output["song"]["notes"] = sections
        # Convertir eventos de CodeName Engine a PsychEngine
    for ev in data.get("events", []):
        time = ev.get("time", 0)
        name = ev.get("name", "")
        params = ev.get("params", [])
        # Primer param como string
        str_params = [str(p) for p in params]
        first_param = str_params[0] if str_params else ""
        rest_params = ",".join(str_params[1:]) if len(str_params) > 1 else ""
        # Agregar el evento al diccionario agrupando por tiempo
        events_dict[time].append([name, first_param, rest_params])
    # Convertir a lista ordenada por tiempo
    output["song"]["events"] = [
        [time, events] for time, events in sorted(events_dict.items())]
    return output
# V-Slice Engine
def convert_vslice_chart(data,meta,diff):
    events_dict = defaultdict(list)
    speed_data = data.get("scrollSpeed",{})
    output = {
        "song": {
            "player1": meta["player1"],
            "player2": meta["player2"],
            "gfVersion": meta["gfVersion"],
            "stage": meta["stage"],
            "events": [],
            "notes": [],
            "song": meta["song"],
            "needsVoices": True,
            "validScore": True,
            "bpm": meta["bpm"],
            "speed": (speed_data.get(diff) or 1),
            "arrowSkin": meta["arrowSkin"],
            "splashSkin": meta["splashSkin"]
        }
    }
    diff_notes = data.get("notes",{}).get(diff,[])
    if not diff_notes:
        messagebox.showwarning("Advertencia:",f"No hay notas para la dificultad: '{diff}'.")
    all_notes = []
    for note in diff_notes:
        psych_note = [note["t"],note["d"],note.get("l",0)]
        if "k" in note:
            psych_note.append(note["k"])
        all_notes.append(psych_note)
    all_notes.sort(key=lambda n: n[0])
    last_note_time = all_notes[-1][0] if all_notes else 0
    current_time = 0
    current_bpm = meta["bpm"]
    section_length = (60000 / current_bpm) * 4
    note_index = 0
    sections = []
    while current_time <= last_note_time:
        current_section = []
        while note_index < len(all_notes) and all_notes[note_index][0] < current_time + section_length:
            current_section.append(all_notes[note_index])
            note_index += 1
        sections.append({
            "typeOfSection": 0,
            "sectionBeats": 4,
            "altAnim": False,
            "gfSection": False,
            "sectionNotes": current_section,
            "mustHitSection": True,
            "changeBPM": False,
            "bpm": current_bpm
        })
        current_time += section_length
    output["song"]["notes"] = sections
    for ev in data.get("events", []):
        time = ev.get("t", 0)
        name = ev.get("e", "")
        values = ev.get("v", {})
        # Convertir todos los valores en strings (en orden consistente)
        str_values = [str(v) for v in values.values()]
        first_values = str_values[0] if str_values else ""
        rest_values = ",".join(str_values[1:]) if len(str_values) > 1 else ""
        # Guardar en el grupo de su tiempo
        events_dict[time].append([name, first_values, rest_values])
    # Ordenar por tiempo y armar la estructura PsychEngine
    output["song"]["events"] = [
        [time, events] for time, events in sorted(events_dict.items())]
    return output
# Elegir conversión
try:
    if chart_type == "codename":
        output_data = convert_codename_chart(input_json,extra_meta)
        song_name = extra_meta["song"]
        output_suffix = ""
    elif chart_type == "vslice":
        output_data = convert_vslice_chart(input_json,extra_meta,vslice_diff)
        song_name = extra_meta["song"]
        output_suffix = f"-{vslice_diff}"  # añadir nombre de la dificultad al archivo
    else:
        raise ValueError("Tipo de chart no válido")
except Exception as e:
    messagebox.showerror("Error",f"No se pudo convertir el chart: {e}")
    exit()
# Guardar con la dificultad si es V-Slice
safe_song_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in song_name)
output_file_path = output_folder / f"{safe_song_name}{output_suffix}_converted.json"
with open(output_file_path,"w",encoding="utf-8") as f:
    json.dump(output_data,f,ensure_ascii=False,indent=2)
# Yo solo hice esto por que si xd,usenlo como ustedes quieran gente,adios :3,80CR4FMA08
print(f"Chart convertido correctamente y guardado en: {output_file_path}")