package dev.acci.legacyvm;

import java.io.*;
import java.nio.file.Files;
import java.util.*;
import java.util.zip.*;

/** Stream only allowlisted files into a private staging directory. */
public final class ProfileImporter {
    private ProfileImporter() {}
    public static void recover(File home) throws IOException {
        File profile = new File(home,"profile"), backup = new File(home,"profile-backup");
        if (!profile.exists() && backup.exists() && !backup.renameTo(profile))
            throw new IOException("Не удалось восстановить прежний профиль из profile-backup");
    }
    public static void remove(File file) throws IOException {
        // Only caller-owned app-private staging/run directories are passed.
        if (Files.isSymbolicLink(file.toPath())) throw new IOException("Unexpected private symlink");
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children == null) throw new IOException("Cannot list private directory");
            for (File child : children) remove(child);
        }
        if (file.exists() && !file.delete()) throw new IOException("Cannot remove private temporary file");
    }
    public static void copyTree(File source, File dest) throws IOException {
        if (Files.isSymbolicLink(source.toPath())) throw new IOException("Unexpected private symlink");
        if (source.isDirectory()) {
            if (!dest.mkdirs() && !dest.isDirectory()) throw new IOException("Cannot create run directory");
            File[] children = source.listFiles();
            if (children == null) throw new IOException("Cannot list profile");
            for (File child : children) copyTree(child, new File(dest, child.getName()));
        } else {
            try (InputStream in = new FileInputStream(source); OutputStream out = new FileOutputStream(dest)) {
                byte[] b = new byte[65536]; int n;
                while ((n = in.read(b)) != -1) out.write(b, 0, n);
            }
        }
    }
    public static String importZip(InputStream stream, File home) throws IOException {
        recover(home);
        File staging = new File(home, "import-" + UUID.randomUUID());
        if (!staging.mkdir()) throw new IOException("Не удалось создать временную папку");
        Set<String> names = new HashSet<>();
        long total = 0;
        int count = 0, pages = 0;
        boolean committed = false;
        try {
            try (ZipInputStream zip = new ZipInputStream(new BufferedInputStream(stream))) {
                ZipEntry entry;
                byte[] buffer = new byte[65536];
                while ((entry = zip.getNextEntry()) != null) {
                    if (++count > ProfileContract.MAX_ENTRIES) throw new IOException("Слишком много файлов");
                    String name = entry.getName();
                    if (!names.add(name)) throw new IOException("Повторяющийся путь в ZIP");
                    if (entry.isDirectory()) {
                        if (!ProfileContract.allowedDirectory(name)) throw new IOException("Недопустимая папка");
                        if (entry.getSize() > 0 || zip.read() != -1) throw new IOException("Данные вместо папки");
                        zip.closeEntry(); continue;
                    }
                    long limit = ProfileContract.limitFor(name), written = 0;
                    File dest = new File(staging, name);
                    if (!dest.getCanonicalPath().startsWith(staging.getCanonicalPath() + File.separator))
                        throw new IOException("Небезопасный путь");
                    if (!dest.getParentFile().mkdirs() && !dest.getParentFile().isDirectory())
                        throw new IOException("Не удалось создать папку");
                    try (OutputStream out = Files.newOutputStream(dest.toPath(), java.nio.file.StandardOpenOption.CREATE_NEW)) {
                        int n;
                        while ((n = zip.read(buffer)) != -1) {
                            written += n; total += n;
                            if (written > limit || total > ProfileContract.MAX_TOTAL)
                                throw new IOException("Лимит распакованного профиля превышен");
                            out.write(buffer, 0, n);
                        }
                    }
                    ProfileContract.size(name, written);
                    if (name.startsWith("nand/")) pages++;
                    zip.closeEntry(); // validates CRC too
                }
            }
            for (String required : new String[]{"manifest.json", "bootrom.bin", "iboot.bin", "nor.bin"})
                if (!names.contains(required)) throw new IOException("В профиле нет " + required + ". IPA не является образом системы.");
            if (pages < 1) throw new IOException("Нет страниц NAND");
            ProfileContract.manifest(Files.readAllBytes(new File(staging, "manifest.json").toPath()));
            for (int bank = 0; bank < 8; bank++) {
                File directory = new File(staging, "nand/bank" + bank);
                if (!directory.mkdirs() && !directory.isDirectory()) throw new IOException("Cannot prepare NAND banks");
            }
            File profile = new File(home, "profile"), previous = new File(home, "profile-backup");
            if (previous.exists()) remove(previous);
            boolean old = profile.exists();
            if (old && !profile.renameTo(previous)) throw new IOException("Не удалось сохранить прежний профиль");
            if (!staging.renameTo(profile)) {
                if (old && !previous.renameTo(profile)) throw new IOException("Нужна проверка profile-backup");
                throw new IOException("Не удалось установить новый профиль");
            }
            committed = true;
            if (previous.exists()) remove(previous);
            return pages + " страниц NAND • структура проверена, загрузка iOS не проверена";
        } catch (ZipException e) {
            throw new IOException("Повреждённый или неподдерживаемый ZIP", e);
        } finally {
            if (!committed && staging.exists()) remove(staging);
        }
    }
}