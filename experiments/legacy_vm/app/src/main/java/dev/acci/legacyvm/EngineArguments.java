package dev.acci.legacyvm;

import java.io.File;
import java.util.*;

/** No shell, networking, host shares, QMP, or user-authored QEMU arguments. */
public final class EngineArguments {
    private EngineArguments() {}
    private static String path(File file) {
        String p = file.getAbsolutePath();
        if (p.indexOf(',') >= 0 || p.indexOf('\0') >= 0) throw new IllegalArgumentException("Invalid internal path");
        return p;
    }
    public static List<String> create(File executable, File run, File guest, File profile) {
        List<String> args = new ArrayList<>();
        Collections.addAll(args, path(executable), "-nodefaults", "-nic", "none",
            "-display", "none", "-vnc", "unix:" + path(new File(run, "vnc.sock")),
            "-monitor", "none", "-serial", "stdio", "-L", path(new File(run, "data")),
            "-no-reboot", "-accel", "tcg,thread=single");
        if (profile == null) {
            Collections.addAll(args, "-M", "versatilepb", "-m", "64M", "-kernel", path(guest));
        } else {
            Collections.addAll(args, "-M", "iPod-Touch,bootrom=" + path(new File(profile, "bootrom.bin")) +
                ",iboot=" + path(new File(profile, "iboot.bin")) + ",nand=" + path(new File(profile, "nand")),
                "-m", "128M", "-drive", "if=pflash,format=raw,snapshot=on,file=" + path(new File(profile, "nor.bin")));
        }
        return args;
    }
}