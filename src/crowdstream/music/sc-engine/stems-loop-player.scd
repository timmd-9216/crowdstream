(
s.waitForBoot {
    // SynthDef con fade in y fade out
    SynthDef(\playLoop, {
        arg buf, amp = 0.5, fadeTime = 1.0, gate = 1;
        var sig, env;

        // Envelope controlado por 'gate'
        env = Env.asr(fadeTime, amp, fadeTime).kr(gate: gate, doneAction: 2);
        sig = PlayBuf.ar(1, buf, loop: 1);
        sig = sig * env;
        Out.ar(0, sig);
    }).add;

    ~buffers = IdentityDictionary.new;
    ~players = IdentityDictionary.new;
    ~filePaths = IdentityDictionary.new;
    ~validStems = ["vocals", "drums", "bass", "piano", "other"];
    ~fadeTime = 1.0; // fade in/out time in seconds

    // Reproducir un stem
    OSCdef(\play_stem, { |msg|
        var stem, path, amp;

        stem = msg[1].asString;
        path = msg[2];
        amp = if(msg.size > 3) { msg[3].asFloat } { 0.5 };

        if (~validStems.includes(stem).not) {
            ("Invalid stem name: %" % stem).warn;
            ^nil;
        };

        postln("Received /play_sound: " ++ stem ++ " | " ++ path ++ " | amp: " ++ amp);

        // Fade out si ya había synth
        if (~players[stem].notNil) {
            ~players[stem].set(\gate, 0); // dispara fade out
        };

        if (~filePaths[stem] == path and: { ~buffers[stem].notNil }) {
            ~players[stem] = Synth(\playLoop, [\buf, ~buffers[stem].bufnum, \amp, amp, \fadeTime, ~fadeTime]);
            ~filePaths[stem] = path;
        } {
            Buffer.read(s, path, action: { |b|
                ~buffers[stem] = b;
                ~filePaths[stem] = path;
                ~players[stem] = Synth(\playLoop, [\buf, b.bufnum, \amp, amp, \fadeTime, ~fadeTime]);
            });
        };
    }, '/play_sound');

    // Ajustar volumen del stem en tiempo real
    OSCdef(\set_volume, { |msg|
        var stem, amp;

        stem = msg[1].asString;
        amp = msg[2].asFloat;

        if (~validStems.includes(stem).not) {
            ("Invalid stem name: %" % stem).warn;
            ^nil;
        };

        if (~players[stem].notNil) {
            ~players[stem].set(\amp, amp);
            postln("Set volume for " ++ stem ++ " → " ++ amp);
        } {
            ("No active synth for stem: %" % stem).warn;
        };
    }, '/set_volume');

    // Detener un stem con fade out
    OSCdef(\stop_stem, { |msg|
        var stem;

        stem = msg[1].asString;

        if (~validStems.includes(stem).not) {
            ("Invalid stem name: %" % stem).warn;
            ^nil;
        };

        if (~players[stem].notNil) {
            ~players[stem].set(\gate, 0); // activa fade out
            ~players[stem] = nil;
            ~filePaths[stem] = nil;
        } {
            ("No active stem to stop: %" % stem).warn;
        };
    }, '/stop_sound');

    // Detener todos los stems activos
    OSCdef(\stop_all, {
        "Received /stop_all".postln;
        ~validStems.do { |stem|
            if (~players[stem].notNil) {
                ~players[stem].set(\gate, 0); // fade out
                ~players[stem] = nil;
                ~filePaths[stem] = nil;
            };
        };
    }, '/stop_all');

    postln("OSC stem player ready with: /play_sound, /set_volume, /stop_sound, /stop_all");
};
)