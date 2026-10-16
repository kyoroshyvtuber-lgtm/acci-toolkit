package dev.acci.legacyvm;

import java.io.*;
import java.nio.charset.StandardCharsets;

/** A bounded raw-only RFB 3.8 client. Only app-private local sockets use it. */
public final class RfbProtocol implements Closeable {
    private final DataInputStream in;
    private final DataOutputStream out;
    private int width, height;
    private int[] pixels;
    public RfbProtocol(InputStream input, OutputStream output) {
        in = new DataInputStream(new BufferedInputStream(input, 65536));
        out = new DataOutputStream(new BufferedOutputStream(output, 65536));
    }
    private byte[] bytes(int length, int limit) throws IOException {
        if (length < 0 || length > limit) throw new IOException("RFB field too large");
        byte[] b = new byte[length]; in.readFully(b); return b;
    }
    public void handshake() throws IOException {
        String version = new String(bytes(12, 12), StandardCharsets.US_ASCII);
        if (!version.equals("RFB 003.008\n")) throw new IOException("Unsupported RFB version");
        synchronized (out) {
            out.write("RFB 003.008\n".getBytes(StandardCharsets.US_ASCII)); out.flush();
        }
        byte[] security = bytes(in.readUnsignedByte(), 255);
        boolean none = false;
        for (byte value : security) if (value == 1) none = true;
        if (!none) throw new IOException("No local RFB security type");
        synchronized (out) { out.writeByte(1); out.flush(); }
        if (in.readInt() != 0) throw new IOException("RFB security failed");
        synchronized (out) { out.writeByte(1); out.flush(); }
        resize(in.readUnsignedShort(), in.readUnsignedShort());
        bytes(16, 16); bytes(in.readInt(), 4096);
        synchronized (out) {
            out.writeInt(0); // SetPixelFormat type + three padding bytes
            out.write(new byte[]{32, 24, 0, 1});
            out.writeShort(255); out.writeShort(255); out.writeShort(255);
            out.write(new byte[]{16, 8, 0, 0, 0, 0});
            out.writeByte(2); out.writeByte(0); out.writeShort(2);
            out.writeInt(0); out.writeInt(-223); // RAW and DesktopSize only
            out.flush();
        }
    }
    private void resize(int w, int h) throws IOException {
        if (w < 1 || h < 1 || w > 2048 || h > 2048) throw new IOException("RFB dimensions");
        width = w; height = h; pixels = new int[w * h];
    }
    public int width() { return width; }
    public int height() { return height; }
    public int[] pixels() { return pixels.clone(); }
    public void frame() throws IOException {
        synchronized (out) {
            out.writeByte(3); out.writeByte(0); out.writeShort(0); out.writeShort(0);
            out.writeShort(width); out.writeShort(height); out.flush();
        }
        while (true) {
            int type = in.readUnsignedByte();
            if (type == 2) continue; // bell
            if (type == 3) { bytes(3, 3); bytes(in.readInt(), 65536); continue; }
            if (type != 0) throw new IOException("Unexpected RFB message");
            in.readUnsignedByte();
            int rectangles = in.readUnsignedShort();
            if (rectangles > 1024) throw new IOException("RFB rectangle limit");
            for (int n = 0; n < rectangles; n++) {
                int x = in.readUnsignedShort(), y = in.readUnsignedShort();
                int w = in.readUnsignedShort(), h = in.readUnsignedShort(), encoding = in.readInt();
                if (encoding == -223) { resize(w, h); continue; }
                if (encoding != 0 || x + w > width || y + h > height)
                    throw new IOException("Unsupported RFB rectangle");
                byte[] row = new byte[w * 4];
                for (int j = 0; j < h; j++) {
                    in.readFully(row);
                    for (int i = 0; i < w; i++) {
                        int offset = i * 4;
                        pixels[(y + j) * width + x + i] = 0xff000000 |
                            ((row[offset + 2] & 255) << 16) |
                            ((row[offset + 1] & 255) << 8) | (row[offset] & 255);
                    }
                }
            }
            return;
        }
    }
    public void key(int keysym, boolean down) throws IOException {
        synchronized (out) {
            out.writeByte(4); out.writeByte(down ? 1 : 0); out.writeShort(0);
            out.writeInt(keysym); out.flush();
        }
    }
    public void pointer(int x, int y, boolean down) throws IOException {
        synchronized (out) {
            out.writeByte(5); out.writeByte(down ? 1 : 0);
            out.writeShort(Math.max(0, Math.min(width - 1, x)));
            out.writeShort(Math.max(0, Math.min(height - 1, y))); out.flush();
        }
    }
    @Override public void close() throws IOException { in.close(); out.close(); }
}