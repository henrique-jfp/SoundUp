from pycaw.pycaw import AudioUtilities

try:
    devices = AudioUtilities.GetAllDevices()
except Exception as exc:  # pragma: no cover
    print("falha ao listar dispositivos:", exc)
    devices = []

for device in devices:
    try:
        print(device.id, "|", device.FriendlyName, "|state=", device.state)
    except Exception as exc:
        print("dispositivo:", exc)

print("=== default ===")
speakers = AudioUtilities.GetSpeakers()
print("id:", speakers.id)
print("nome:", speakers.FriendlyName)
