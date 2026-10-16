package dev.acci.legacyvm;

import android.content.Context;
import android.net.LocalSocket;
import android.net.LocalSocketAddress;
import android.os.Build;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.concurrent.*;

/** Owns exactly one child process; never exposes a network listener. */
public final class EngineController {
    public interface Listener {
        void state(String message, boolean running, boolean display);
        void frame(int width, int height, int[] pixels);
    }
    private final Context context;
    private final Listener listener;
    private volatile Process process;
    private volatile LocalSocket socket;
    private volatile RfbProtocol rfb;
    private volatile boolean running, stopRequested, boot, input;
    private volatile int frames;
    private volatile boolean selfTest;
    private volatile String lastError = "";
    private long generation;
    private final Object evidenceLock = new Object();
    private final StringBuilder log = new StringBuilder();
    private final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor();
    private final ThreadPoolExecutor inputs = new ThreadPoolExecutor(1,1,0,TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(32), new ThreadPoolExecutor.DiscardOldestPolicy());
    private ScheduledFuture<?> deadline;
    public EngineController(Context context, Listener listener) {
        this.context = context.getApplicationContext(); this.listener = listener;
    }
    public boolean running() { return running; }
    public synchronized void start(boolean self) {
        if (running) return;
        running = true; stopRequested = false; selfTest = self;
        boot = false; input = false; frames = 0; lastError = "";
        synchronized (log) { log.setLength(0); }
        listener.state("Подготовка движка…", true, false);
        long session = ++generation;
        deadline = timer.schedule(() -> {
            synchronized (EngineController.this) {
                if (running && generation == session) stop("Остановлено по лимиту времени");
            }
        }, self ? 90 : 600, TimeUnit.SECONDS);
        new Thread(() -> execute(self), "acci-engine").start();
    }
    private void execute(boolean self) {
        File run = new File(context.getFilesDir(), "run");
        Thread reader = null;
        try {
            if (run.exists()) ProfileImporter.remove(run);
            if (!new File(run, "empty").mkdirs()) throw new IOException("Cannot create private run directory");
            File guest = new File(run, "smoke.elf");
            File profile = null;
            if (self) {
                try (InputStream in = context.getAssets().open("generated/smoke.elf");
                     OutputStream out = new FileOutputStream(guest)) { transfer(in, out); }
            } else {
                File original = new File(context.getFilesDir(), "profile");
                if (!new File(original, "manifest.json").isFile()) throw new IOException("Сначала импортируйте профиль");
                profile = new File(run, "p");
                ProfileImporter.copyTree(original, profile); // original profile never passed to QEMU
            }
            File executable = new File(context.getApplicationInfo().nativeLibraryDir, "libacci_qemu.so");
            if (!executable.isFile()) throw new IOException("Нет движка для ABI этого устройства");
            if (new File(run, "vnc.sock").getAbsolutePath().getBytes(StandardCharsets.UTF_8).length > 100)
                throw new IOException("Private socket path is too long");
            if (stopRequested) return;
            ProcessBuilder builder = new ProcessBuilder(EngineArguments.create(executable, run, guest, profile));
            builder.directory(run); builder.redirectErrorStream(true);
            builder.environment().clear();
            builder.environment().put("HOME", run.getAbsolutePath());
            builder.environment().put("TMPDIR", run.getAbsolutePath());
            builder.environment().put("LANG", "C");
            process = builder.start();
            if (stopRequested) { process.destroy(); return; }
            reader = new Thread(this::readLog, "acci-uart"); reader.start();
            long timeout = System.nanoTime() + TimeUnit.SECONDS.toNanos(25);
            File sock = new File(run, "vnc.sock");
            while (!stopRequested && process.isAlive() && !sock.exists() && System.nanoTime() < timeout) Thread.sleep(50);
            if (stopRequested) return;
            if (!process.isAlive()) throw new IOException("Движок завершился до подключения экрана: " + tail());
            if (!sock.exists()) throw new IOException("Нет локального экрана за 25 секунд");
            LocalSocket connection = new LocalSocket();
            socket = connection;
            connection.connect(new LocalSocketAddress(sock.getAbsolutePath(), LocalSocketAddress.Namespace.FILESYSTEM));
            connection.setSoTimeout(10000);
            RfbProtocol client = new RfbProtocol(connection.getInputStream(), connection.getOutputStream());
            rfb = client;
            client.handshake();
            listener.state(self ? "ARM-гость запущен • ожидаем кадр" : "Экспериментальная машина запущена", true, true);
            boolean shownBoot = false, shownInput = false;
            while (!stopRequested && process.isAlive()) {
                client.frame(); frames++;
                listener.frame(client.width(), client.height(), client.pixels());
                if (frames == 1 || frames % 20 == 0) evidence();
                if (frames == 1 || shownBoot != boot || shownInput != input) {
                    listener.state(status(), true, true);
                    shownBoot = boot; shownInput = input;
                }
                Thread.sleep(120);
            }
        } catch (Exception e) {
            if (!stopRequested) {
                lastError = e.getClass().getSimpleName() + ": " + e.getMessage();
                listener.state("Ошибка: " + lastError, true, false);
            }
        } finally {
            RfbProtocol old = rfb; rfb = null;
            LocalSocket oldSocket = socket; socket = null;
            try { if (oldSocket != null) oldSocket.close(); } catch (IOException ignored) {}
            // Closing the socket unblocks the reader before closing buffered streams.
            try { if (old != null) old.close(); } catch (IOException ignored) {}
            Process child = process;
            if (child != null) {
                child.destroy();
                try { if (!child.waitFor(3, TimeUnit.SECONDS)) { child.destroyForcibly(); child.waitFor(3, TimeUnit.SECONDS); } }
                catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            }
            try { if (reader != null) reader.join(1000); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            process = null;
            synchronized (this) { running = false; if (deadline != null) deadline.cancel(false); }
            evidence();
            try { Files.write(new File(context.getFilesDir(), "engine.log").toPath(), tail().getBytes(StandardCharsets.UTF_8)); }
            catch (IOException ignored) {}
            listener.state(lastError.isEmpty() ? "Движок остановлен • " + frames + " кадров" : "Ошибка: " + lastError, false, false);
        }
    }
    private static void transfer(InputStream in, OutputStream out) throws IOException {
        byte[] b = new byte[65536]; int n; while ((n = in.read(b)) != -1) out.write(b, 0, n);
    }
    private String status() {
        if (!selfTest) return "Кадры: " + frames + " • загрузка iOS не подтверждена";
        return "ARM • экран подключён • " + (boot ? "BOOT OK" : "ожидаем UART") + (input ? " • INPUT OK" : "");
    }
    private void readLog() {
        Process child = process;
        if (child == null) return;
        try (InputStream in = child.getInputStream()) {
            byte[] b = new byte[4096]; int n, total = 0;
            while ((n = in.read(b)) != -1) {
                total += n;
                synchronized (log) {
                    log.append(new String(b, 0, n, StandardCharsets.UTF_8));
                    if (log.length() > 65536) log.delete(0, log.length() - 65536);
                    if (selfTest && log.indexOf("ACCI_VM_BOOT_OK") >= 0) boot = true;
                    if (selfTest && log.indexOf("ACCI_INPUT_OK") >= 0) input = true;
                }
                evidence();
                if (total > 4 * 1024 * 1024) { lastError = "Лимит журнала превышен"; stop("Лимит журнала"); return; }
            }
        } catch (IOException ignored) {}
    }
    public String tail() { synchronized (log) { return log.toString(); } }
    public void key() {
        RfbProtocol client = rfb; if (client == null) return;
        inputs.execute(() -> {
            try { client.key('a', true); client.key('a', false); }
            catch (IOException ignored) {}
        });
    }
    public void pointer(int x, int y, boolean down) {
        RfbProtocol client = rfb; if (client == null) return;
        inputs.execute(() -> { try { client.pointer(x, y, down); } catch (IOException ignored) {} });
    }
    public void stop(String why) {
        stopRequested = true;
        LocalSocket connection = socket; try { if (connection != null) connection.close(); } catch (IOException ignored) {}
        Process child = process; if (child != null) child.destroy();
    }
    public void dispose() { stop("Закрытие приложения"); timer.shutdownNow(); inputs.shutdownNow(); }
    private void evidence() {
        synchronized (evidenceLock) {
            try {
                JSONObject o = new JSONObject();
                o.put("self_test", selfTest); o.put("ios_boot_verified", false); o.put("safari_verified", false);
                o.put("uart_boot", boot); o.put("uart_input", input); o.put("frames", frames);
                o.put("running", running); o.put("error", lastError);
                o.put("abi", Build.SUPPORTED_ABIS[0]); o.put("sdk", Build.VERSION.SDK_INT);
                o.put("engine_commit", ProfileContract.ENGINE);
                File tmp = new File(context.getFilesDir(), "last-run.tmp"), dest = new File(context.getFilesDir(), "last-run.json");
                Files.write(tmp.toPath(), o.toString(2).getBytes(StandardCharsets.UTF_8));
                Files.move(tmp.toPath(), dest.toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
            } catch (Exception ignored) {} // evidence file is supplemental, never faked in UI
        }
    }
}