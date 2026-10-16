package dev.acci.legacyvm;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.junit.Test;
import static org.junit.Assert.*;

public class ContractTest {
    private void manifest(String s) throws Exception { ProfileContract.manifest(s.getBytes(StandardCharsets.UTF_8)); }
    private String valid() { return "{\"schema\":1,\"machine\":\"ipod-touch-1g\",\"engineCommit\":\"" + ProfileContract.ENGINE + "\"}"; }
    @Test public void acceptsManifest() throws Exception { manifest(valid()); }
    @Test(expected=IOException.class) public void rejectsDuplicateKey() throws Exception { manifest(valid().replace("\"schema\":1", "\"schema\":1,\"schema\":1")); }
    @Test(expected=IOException.class) public void rejectsWrongDevice() throws Exception { manifest(valid().replace("ipod-touch-1g", "iphone-16")); }
    @Test(expected=IOException.class) public void rejectsManifestSuffix() throws Exception { manifest(valid() + " x"); }
    @Test(expected=IOException.class) public void rejectsTraversal() throws Exception { ProfileContract.limitFor("nand/bank0/../../outside"); }
    @Test(expected=IOException.class) public void rejectsIpa() throws Exception { ProfileContract.limitFor("Payload/Safari.app/Safari"); }
    @Test(expected=IOException.class) public void rejectsWrongPageSize() throws Exception { ProfileContract.size("nand/bank0/42.page", 2048); }
    @Test public void acceptsActualPageContract() throws Exception { ProfileContract.size("nand/bank7/206851.page", 2112); }
    @Test public void testArgumentsAreOffline() {
        List<String> a = EngineArguments.create(new File("/app/lib/q.so"), new File("/app/run"), new File("/app/guest.elf"), null);
        assertTrue(a.contains("versatilepb")); assertTrue(a.contains("none"));
        assertFalse(a.contains("shell")); assertFalse(a.contains("-netdev")); assertFalse(a.contains("-virtfs"));
        assertTrue(a.contains("unix:/app/run/vnc.sock"));
    }
    @Test public void testLegacyArgumentsKeepOriginalNor() {
        List<String> a = EngineArguments.create(new File("/app/lib/q.so"), new File("/app/run"), null, new File("/app/profile"));
        assertTrue(a.stream().anyMatch(s -> s.startsWith("iPod-Touch,bootrom=")));
        assertTrue(a.stream().anyMatch(s -> s.contains("snapshot=on,file=/app/profile/nor.bin")));
    }
}