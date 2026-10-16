package dev.acci.legacyvm;

import java.io.*;
import java.nio.charset.StandardCharsets;
import org.junit.Test;
import static org.junit.Assert.*;

public class RfbTest {
    private byte[] server(int width, int height, int encoding) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        DataOutputStream s = new DataOutputStream(bytes);
        s.write("RFB 003.008\n".getBytes(StandardCharsets.US_ASCII));
        s.write(new byte[]{1,1}); s.writeInt(0);
        s.writeShort(width); s.writeShort(height); s.write(new byte[16]);
        s.writeInt(4); s.write("TEST".getBytes(StandardCharsets.US_ASCII));
        if (width == 1 && height == 1) {
            s.writeByte(0); s.writeByte(0); s.writeShort(1);
            s.writeShort(0); s.writeShort(0); s.writeShort(1); s.writeShort(1); s.writeInt(encoding);
            s.write(new byte[]{0x33,0x22,0x11,0});
        }
        return bytes.toByteArray();
    }
    @Test public void handshakeAndLittleEndianPixels() throws Exception {
        RfbProtocol r = new RfbProtocol(new ByteArrayInputStream(server(1,1,0)),new ByteArrayOutputStream());
        r.handshake(); r.frame(); assertEquals(0xff112233,r.pixels()[0]);
    }
    @Test(expected=IOException.class) public void rejectsLargeFramebuffer() throws Exception {
        new RfbProtocol(new ByteArrayInputStream(server(4096,4096,0)),new ByteArrayOutputStream()).handshake();
    }
    @Test(expected=IOException.class) public void rejectsUnsupportedEncoding() throws Exception {
        RfbProtocol r = new RfbProtocol(new ByteArrayInputStream(server(1,1,7)),new ByteArrayOutputStream());
        r.handshake(); r.frame();
    }
    @Test public void inputUsesRfbNotAShell() throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        RfbProtocol r = new RfbProtocol(new ByteArrayInputStream(server(1,1,0)),output);
        r.handshake(); output.reset(); r.key(97,true);
        assertArrayEquals(new byte[]{4,1,0,0,0,0,0,97},output.toByteArray());
    }
}