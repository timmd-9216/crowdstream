from pythonosc import dispatcher, osc_server
def on_person_count(addr, val): print(addr, val)
def on_movement(addr, val): print(addr, val)
def on_keypoints(addr, *vals): print(addr, len(vals), "vals")

disp = dispatcher.Dispatcher()
disp.map("/dance/person_count", on_person_count)
disp.map("/dance/*movement", on_movement)
disp.map("/dance/pose/person/*/keypoints", on_keypoints)
disp.map("/pose/keypoints", on_keypoints)  # legacy

server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", 57120), disp)
print("Listening on", server.server_address)
server.serve_forever()


