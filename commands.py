def handle_command(api, message):
    text = message.text.lower()
    room_id = message.roomId

    if text.startswith('hello'):
        api.messages.create(roomId=room_id, text="Hello! How can I assist you today?")
    elif text.startswith('help'):
        api.messages.create(roomId=room_id, text="Here are the commands you can use:\n1. hello\n2. help")
    else:
        api.messages.create(roomId=room_id, text="Sorry, I didn't understand that command.")
