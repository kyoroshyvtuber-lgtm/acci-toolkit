package dev.acci.legacyvm;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.zip.*;
import org.junit.Test;
import static org.junit.Assert.*;

public class ImportTest {
    private byte[] zip(boolean valid, boolean badDirectory) throws Exception {
        ByteArrayOutputStream result = new ByteArrayOutputStream();
        try (ZipOutputStream z = new ZipOutputStream(result)) {
            String manifest = "{\"schema\":1,\"machine\":\"ipod-touch-1g\",\"engineCommit\":\"" + ProfileContract.ENGINE + "\"}";
            for (String path : new String[]{"manifest.json","bootrom.bin","iboot.bin","nor.bin","nand/bank0/1.page"}) {
                z.putNextEntry(new ZipEntry(path));
                if (path.equals("manifest.json")) z.write(manifest.getBytes(StandardCharsets.UTF_8));
                else z.write(new byte[path.equals("nor.bin") ? 1048576 : path.endsWith(".page") ? 2112 : 32]);
                z.closeEntry();
            }
            if (!valid) { z.putNextEntry(new ZipEntry("../outside")); z.write(1); z.closeEntry(); }
            if (badDirectory) { z.putNextEntry(new ZipEntry("nand/")); z.write(1); z.closeEntry(); }
        }
        return result.toByteArray();
    }
    @Test public void importsSyntheticProfileWithoutAppleBytes() throws Exception {
        File home = Files.createTempDirectory("import-test").toFile();
        try {
            String info = ProfileImporter.importZip(new ByteArrayInputStream(zip(true,false)),home);
            assertTrue(info.contains("загрузка iOS не проверена"));
            assertTrue(new File(home,"profile/nand/bank7").isDirectory());
            assertEquals(1048576,new File(home,"profile/nor.bin").length());
        } finally { ProfileImporter.remove(home); }
    }
    @Test public void failedImportPreservesPreviousProfile() throws Exception {
        File home = Files.createTempDirectory("import-test").toFile();
        try {
            new File(home,"profile").mkdir(); File marker = new File(home,"profile/original");
            Files.write(marker.toPath(),new byte[]{42});
            try { ProfileImporter.importZip(new ByteArrayInputStream(zip(false,false)),home); fail("Unsafe ZIP accepted"); }
            catch (IOException expected) { assertEquals(42,Files.readAllBytes(marker.toPath())[0]); }
            assertFalse(new File(home.getParentFile(),"outside").exists());
        } finally { ProfileImporter.remove(home); }
    }
    @Test(expected=IOException.class) public void rejectsDataInDirectoryEntry() throws Exception {
        File home = Files.createTempDirectory("import-test").toFile();
        try { ProfileImporter.importZip(new ByteArrayInputStream(zip(true,true)),home); }
        finally { ProfileImporter.remove(home); }
    }
}