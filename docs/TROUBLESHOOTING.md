# Troubleshooting Guide

## IPv4/IPv6 Network Issue on macOS

### Problem
OSC messages are sent but not received by the audio server, causing commands like `instant.bass denmark` to appear successful in the mixer but produce no audio.

### Symptoms
- Mixer shows stem loading successfully (e.g., "📥 Smart loading: bass from Denmark → buffer 1000")
- Mixer shows playback status (e.g., "▶️ 🔄 buffer 1000 | rate: 0.893")
- No audio is heard
- `tcpdump` shows UDP packets being sent to the correct port
- Audio server never shows "📡 OSC RECEIVED" messages

### Root Cause
**IPv4/IPv6 Address Resolution Mismatch**

On macOS, when using `"localhost"` as the hostname:
- **OSC Client** (mixer) resolves `"localhost"` to IPv6 (`::1`) and sends packets via IPv6
- **OSC Server** (audio server) binds to `"localhost"` which may resolve to IPv4 (`127.0.0.1`)
- Result: Client sends IPv6 packets but server only listens on IPv4

This can be confirmed with `tcpdump`:
```bash
sudo tcpdump -i lo0 udp port 57120
# Shows: IP6 localhost.xxxxx > localhost.57120: UDP
#        ^^^ IPv6 traffic but server listening on IPv4
```

### Solution

#### 1. Fix Audio Server Binding
In `audio_server.py`, change the OSC server to bind to all interfaces:

```python
# Before (problematic):
self.osc_server = ThreadingOSCUDPServer(("localhost", self.osc_port), disp)

# After (fixed):
self.osc_server = ThreadingOSCUDPServer(("0.0.0.0", self.osc_port), disp)
```

#### 2. Fix Client Address Resolution  
In `stem_mixer_smart.py`, force IPv4 resolution:

```python
# Before (problematic):
self.sc_client = udp_client.SimpleUDPClient(sc_host, sc_port)

# After (fixed):
sc_host_ipv4 = "127.0.0.1" if sc_host == "localhost" else sc_host
self.sc_client = udp_client.SimpleUDPClient(sc_host_ipv4, sc_port)
```

### Why This Happens on macOS

1. **Dual Stack Networking**: macOS supports both IPv4 and IPv6 simultaneously
2. **Localhost Resolution**: `"localhost"` can resolve to either `127.0.0.1` (IPv4) or `::1` (IPv6)
3. **Python OSC Library**: The python-osc library's client and server may resolve `"localhost"` differently
4. **Default Behavior**: macOS may prefer IPv6 for outbound connections but Python may default to IPv4 for server binding

### Verification

After applying the fix, you should see:
- `tcpdump` showing IPv4 traffic: `IP 127.0.0.1.xxxxx > 127.0.0.1.57120`
- Audio server logging: `📡 OSC RECEIVED: /load_buffer [...]`
- Actual audio playback when using commands like `instant.bass denmark`

### Alternative Solutions

If the above doesn't work, try these alternatives:

1. **Force IPv6 for both client and server**:
   ```python
   # Server: bind to IPv6
   self.osc_server = ThreadingOSCUDPServer(("::", self.osc_port), disp)
   # Client: use IPv6 localhost
   self.sc_client = udp_client.SimpleUDPClient("::1", sc_port)
   ```

2. **Disable IPv6 system-wide** (not recommended):
   ```bash
   # Temporarily disable IPv6 (requires restart)
   sudo sysctl -w net.inet6.ip6.disable=1
   ```

3. **Use explicit IP addresses everywhere**:
   - Replace all instances of `"localhost"` with `"127.0.0.1"`
   - Ensures consistent IPv4 usage

### Related Issues

This issue may also affect:
- Other OSC-based applications on macOS
- Python applications using socket libraries with `"localhost"`
- Docker containers with networking issues on macOS
- Any client-server communication relying on localhost resolution

### Prevention

For future projects:
- Always use explicit IP addresses (`127.0.0.1`, `::1`) instead of `"localhost"`
- Test network communication with `tcpdump` or `netstat`
- Consider binding servers to `0.0.0.0` (all IPv4) or `::` (all IPv6)
- Document network requirements clearly

---

## Performance Issues with Real-Time EQ Filters

### Problem
Audio glitches, stuttering, dropouts, or high CPU usage when real-time EQ filters are enabled.

### Symptoms
- Audio dropouts or crackling sounds
- High CPU usage (80-100% on Raspberry Pi or Mac M1)
- Audio buffer underruns
- System becomes unresponsive
- "Audio loop exceeded budget" warnings in logs

### Root Cause
**CPU-Intensive Real-Time Processing**

Real-time EQ filters (3-band: low/mid/high) require significant CPU resources:
- Each audio chunk must be processed through multiple IIR filters
- Processing happens in the critical audio thread (must complete within buffer time)
- On lower-powered systems (Raspberry Pi, Mac M1), this can exceed the audio buffer budget

### Solutions

#### Raspberry Pi
- **EQ filters are disabled by default** on Raspberry Pi
- If you enabled them with `--enable-filters` and experience issues:
  ```bash
  # Remove --enable-filters flag from scripts/audio-mix-start.sh
  python audio_server.py --port 57122  # Without --enable-filters
  ```
- For better performance, use optimized filters (requires scipy):
  ```bash
  python audio_server.py --port 57122 --optimized-filters
  ```
- Increase buffer size to reduce CPU pressure:
  ```bash
  python audio_server.py --port 57122 --buffer-size 2048  # Higher latency but more stable
  ```

#### Mac M1
- **EQ filters are disabled by default** on Mac M1
- Real-time EQ processing can cause audio dropouts and high CPU usage
- To disable filters:
  ```bash
  python audio_server.py --port 57122  # Filters disabled by default on M1
  ```
- If you need EQ control, consider:
  - Using external hardware EQs
  - Using software EQs outside the audio server
  - Upgrading to M2 Pro/Max/Ultra (filters enabled by default)

#### General Recommendations
- **Monitor CPU usage**: Use `top` or `htop` to verify impact
- **Use filters only on powerful systems**: M2 Pro/Max/Ultra, desktop CPUs
- **Increase buffer size**: Higher buffer = more CPU headroom but higher latency
- **Consider alternatives**: External hardware EQs or software EQs outside the audio server
- **Test incrementally**: Enable filters and monitor performance before using in production

### Performance Testing

To verify if EQ filters are causing issues:

```bash
# Without filters (baseline)
python audio_server.py --port 57122
# Monitor CPU: should be < 30% on desktop, < 50% on RPi

# With filters
python audio_server.py --port 57122 --enable-filters
# Monitor CPU: may spike to 80-100% on RPi/M1

# With optimized filters (if scipy available)
python audio_server.py --port 57122 --optimized-filters
# Should be 50-100x faster than standard filters
```

### Related Configuration

The system automatically detects the platform and sets defaults:
- **Raspberry Pi**: Filters disabled by default
- **Mac M1**: Filters disabled by default  
- **Mac M2 Pro/Max/Ultra**: Filters enabled by default
- **Other systems**: Filters disabled by default

You can override defaults with:
- `--enable-filters`: Force enable filters
- `--disable-filters`: Force disable filters