package dev.acci.legacyvm;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Pattern;

/** Structural validation only; cannot establish authenticity or bootability. */
public final class ProfileContract {
    public static final String ENGINE = "501c85c4f8a3503965e38d5d4f30a02c4bc9171c";
    public static final long MAX_TOTAL = 384L * 1024 * 1024;
    public static final int MAX_ENTRIES = 150000;
    private static final Pattern PAGE = Pattern.compile("nand/bank[0-7]/(?:0|[1-9][0-9]{0,6})\\.page");
    private ProfileContract() {}
    public static long limitFor(String name) throws IOException {
        if (name.equals("manifest.json")) return 4096;
        if (name.equals("bootrom.bin")) return 65536;
        if (name.equals("iboot.bin")) return 4 * 1024 * 1024;
        if (name.equals("nor.bin")) return 1048576;
        if (PAGE.matcher(name).matches()) return 2112;
        throw new IOException("Недопустимый файл в профиле: " + shortName(name));
    }
    private static String shortName(String name) {
        return name.replaceAll("[\\p{Cntrl}]", "?").substring(0, Math.min(80, name.length()));
    }
    public static void size(String name, long bytes) throws IOException {
        long limit = limitFor(name);
        if (bytes < 1 || bytes > limit ||
            (name.equals("nor.bin") && bytes != limit) ||
            (PAGE.matcher(name).matches() && bytes != 2112))
            throw new IOException("Неверный размер: " + shortName(name));
    }
    public static boolean allowedDirectory(String name) {
        return name.equals("nand/") || name.matches("nand/bank[0-7]/");
    }
    public static void manifest(byte[] data) throws IOException {
        if (data.length > 4096) throw new IOException("Manifest too large");
        // Intentionally small JSON grammar: three scalar fields, no escapes,
        // duplicate keys, extra fields, nested values or executable arguments.
        String text = new String(data, StandardCharsets.UTF_8);
        Scanner parser = new Scanner(text);
        Map<String, String> fields = parser.object();
        if (fields.size() != 3 || !"#1".equals(fields.get("schema")) ||
            !"ipod-touch-1g".equals(fields.get("machine")) ||
            !ENGINE.equals(fields.get("engineCommit")))
            throw new IOException("Нужен профиль ipod-touch-1g для закреплённого движка");
    }
    private static final class Scanner {
        final String source; int at;
        Scanner(String source) { this.source = source; }
        void spaces() { while (at < source.length() && " \t\r\n".indexOf(source.charAt(at)) >= 0) at++; }
        void expect(char c) throws IOException {
            spaces(); if (at >= source.length() || source.charAt(at++) != c) throw new IOException("Invalid manifest");
        }
        String string() throws IOException {
            expect('"'); int start = at;
            while (at < source.length() && source.charAt(at) != '"') {
                char c = source.charAt(at++);
                if (!(Character.isLetterOrDigit(c) && c < 128) && c != '-') throw new IOException("Invalid manifest string");
            }
            String result = source.substring(start, at); expect('"'); return result;
        }
        Map<String, String> object() throws IOException {
            Map<String, String> map = new HashMap<>(); expect('{'); spaces();
            while (at < source.length() && source.charAt(at) != '}') {
                String key = string(); expect(':'); spaces();
                String value;
                if (at < source.length() && source.charAt(at) == '"') value = string();
                else { expect('1'); value = "#1"; }
                if (map.put(key, value) != null || map.size() > 3) throw new IOException("Duplicate/extra field");
                spaces();
                if (at < source.length() && source.charAt(at) == '}') break;
                expect(','); spaces();
                if (at < source.length() && source.charAt(at) == '}') throw new IOException("Trailing comma");
            }
            expect('}'); spaces(); if (at != source.length()) throw new IOException("Manifest suffix");
            return map;
        }
    }
}