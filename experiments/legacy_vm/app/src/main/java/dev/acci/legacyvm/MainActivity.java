package dev.acci.legacyvm;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public final class MainActivity extends Activity implements EngineController.Listener {
    private static final int BG = Color.rgb(13,17,23), PANEL = Color.rgb(22,27,34);
    private static final int FG = Color.rgb(230,237,243), MUTED = Color.rgb(159,172,188), BLUE = Color.rgb(88,166,255);
    private static final int PICK_PROFILE = 30;
    private EngineController engine;
    private GuestView guest;
    private TextView status, profileStatus;
    private Button start, stop, key, importButton, runProfile;
    private boolean importing;
    private int dp(float x) { return Math.round(x*getResources().getDisplayMetrics().density); }
    private LinearLayout column() {
        LinearLayout c = new LinearLayout(this); c.setOrientation(LinearLayout.VERTICAL); return c;
    }
    private GradientDrawable surface(int color, int border) {
        GradientDrawable b = new GradientDrawable(); b.setColor(color); b.setCornerRadius(dp(8));
        if (border != 0) b.setStroke(dp(1), border); return b;
    }
    private TextView text(String value, int size, int color, boolean bold) {
        TextView t = new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(color);
        t.setLineSpacing(dp(3), 1.12f); t.setIncludeFontPadding(false);
        if (bold) t.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        return t;
    }
    private void add(LinearLayout parent, View view, int top) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.topMargin = dp(top); parent.addView(view, lp);
    }
    private Button button(String label, int id, boolean primary, View.OnClickListener action) {
        Button b = new Button(this); b.setId(id); b.setText(label); b.setTextSize(16); b.setAllCaps(false);
        b.setTextColor(primary ? Color.WHITE : FG);
        b.setBackground(surface(primary ? Color.rgb(31,111,235) : Color.rgb(33,38,45),
            primary ? Color.rgb(88,166,255) : Color.rgb(110,125,145)));
        b.setMinHeight(dp(48)); b.setMinimumHeight(dp(48));
        b.setPadding(dp(16),dp(10),dp(16),dp(10)); b.setOnClickListener(action); return b;
    }
    private LinearLayout card(LinearLayout parent, String heading) {
        LinearLayout c = column(); c.setPadding(dp(16),dp(16),dp(16),dp(16));
        c.setBackground(surface(PANEL, Color.rgb(48,54,61)));
        add(c,text(heading,20,FG,true),0); add(parent,c,24); return c;
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try { ProfileImporter.recover(getFilesDir()); } catch (IOException ignored) {}
        engine = new EngineController(this, this);
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true); scroll.setBackgroundColor(BG);
        LinearLayout page = column(); page.setPadding(dp(20),dp(24),dp(20),dp(32));
        LinearLayout.LayoutParams content = new LinearLayout.LayoutParams(-1,-2);
        page.setLayoutParams(content); scroll.addView(page);
        scroll.setOnApplyWindowInsetsListener((v, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                scroll.setPadding(bars.left,bars.top,bars.right,bars.bottom);
            } else scroll.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        add(page,text("ACCI  /  LEGACY VM",14,BLUE,true),0);
        add(page,text("Запускаем код.\nПроверяем результат.",28,FG,true),12);
        add(page,text("Локальный прототип ARM-эмулятора. Без сервера и без подмены iOS веб-страницей.",16,MUTED,false),12);
        LinearLayout vm = card(page,"Виртуальная машина");
        status = text("Готов к проверке • движок не запущен",14,MUTED,false);
        status.setId(R.id.engine_status); status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        add(vm,status,12);
        guest = new GuestView(this); guest.setId(R.id.guest_framebuffer); guest.controller(engine);
        add(vm,guest,16);
        start = button("Запустить ARM-тест",R.id.start_self_test,true,v -> {
            guest.clear(); engine.start(true);
        }); add(vm,start,16);
        LinearLayout actions = new LinearLayout(this); actions.setOrientation(LinearLayout.HORIZONTAL);
        key = button("Ввод A",R.id.send_test_key,false,v -> engine.key());
        stop = button("Стоп",R.id.stop_engine,false,v -> engine.stop("Остановлено пользователем"));
        LinearLayout.LayoutParams half = new LinearLayout.LayoutParams(0,-2,1); half.rightMargin=dp(8);
        actions.addView(key,half); actions.addView(stop,new LinearLayout.LayoutParams(0,-2,1)); add(vm,actions,12);
        add(vm,text("Тест исполняет наш ARM-код: экран → клавиша → ответ гостя. Это не iOS. Остановка через 90 секунд или при уходе из приложения.",14,MUTED,false),12);
        Button journal = button("Журнал движка",R.id.show_log,false,v -> showLog()); add(vm,journal,12);
        LinearLayout profile = card(page,"Образ старого устройства");
        add(profile,text("Экспериментальный профиль iPod touch 1G. Загрузка iOS и Safari пока не подтверждена. Современные IPA сюда не устанавливаются.",16,FG,false),12);
        profileStatus = text(profileExists() ? "Профиль сохранён • загрузка не проверена" : "Образ не добавлен. Apple-файлов в APK нет.",14,MUTED,false);
        add(profile,profileStatus,12);
        importButton = button("Импортировать профиль ZIP",R.id.import_profile,false,v -> chooseProfile());
        add(profile,importButton,16);
        runProfile = button("Пробный запуск профиля",R.id.run_profile,false,v -> {
            new AlertDialog.Builder(this).setTitle("Экспериментальная машина")
                .setMessage("Только доверенные образы, на использование которых у вас есть право. Нет сети, Apple ID или гарантии загрузки. Изменения гостя одноразовые; исходный профиль не меняется. Лимит — 10 минут.")
                .setNegativeButton("Отмена",null)
                .setPositiveButton("Запустить",(d,w) -> { guest.clear(); engine.start(false); }).show();
        }); add(profile,runProfile,12);
        TextView contract = text("Формат: manifest.json, bootrom.bin, iboot.bin, nor.bin и nand/bank0…7/*.page. Только структура — не проверка совместимости.",14,MUTED,false);
        add(profile,contract,12);
        LinearLayout about = card(page,"Открытый и проверяемый");
        add(about,text("QEMU 6.2.50 • GPL-2.0\nОболочка и тестовый гость • MIT\nХост: Android 9+, ARM64 / x86_64\nТестовый гость: ARM32",16,FG,false),12);
        TextView source = text("Исходники, лицензии и инструкции",16,BLUE,true);
        source.setMinHeight(dp(48)); source.setGravity(Gravity.CENTER_VERTICAL); source.setFocusable(true);
        source.setOnClickListener(v -> {
            String revision = "acci/safari-investigation";
            try (InputStream in = getAssets().open("generated/build-identity.json");
                 ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] b = new byte[4096]; int n;
                while ((n=in.read(b))!=-1) { if(out.size()+n>65536) throw new IOException("Identity size"); out.write(b,0,n); }
                String commit = new org.json.JSONObject(new String(out.toByteArray(),StandardCharsets.UTF_8)).getString("app_source_commit");
                if (commit.matches("[0-9a-f]{40}")) revision=commit;
            } catch (Exception ignored) {}
            Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/tree/"+revision+"/experiments/legacy_vm"));
            try { startActivity(i); } catch (ActivityNotFoundException ignored) {}
        });
        add(about,source,12);
        add(about,button("Лицензии компонентов",R.id.show_licenses,false,v -> showLicenses()),8);
        add(about,text("0.1.0 · экспериментальный APK\nНи установка IPA, ни Safari на Android ещё не реализованы.",14,MUTED,false),12);
        setContentView(scroll);
        controls(false,false);
        scroll.requestApplyInsets();
    }
    private boolean profileExists() { return new File(getFilesDir(),"profile/manifest.json").isFile(); }
    private void controls(boolean running, boolean display) {
        start.setEnabled(!running && !importing); start.setAlpha(start.isEnabled()?1:.5f);
        key.setEnabled(running && display); key.setAlpha(key.isEnabled()?1:.5f);
        stop.setEnabled(running); stop.setAlpha(stop.isEnabled()?1:.5f);
        importButton.setEnabled(!running && !importing); importButton.setAlpha(importButton.isEnabled()?1:.5f);
        runProfile.setEnabled(!running && !importing && profileExists()); runProfile.setAlpha(runProfile.isEnabled()?1:.5f);
    }
    @Override public void state(String message, boolean running, boolean display) {
        runOnUiThread(() -> { status.setText(message); controls(running,display); });
    }
    @Override public void frame(int width, int height, int[] pixels) {
        runOnUiThread(() -> guest.frame(width,height,pixels));
    }
    private void chooseProfile() {
        if (profileExists()) new AlertDialog.Builder(this).setTitle("Заменить сохранённый профиль?")
            .setMessage("Прежний профиль сохранится, если импорт нового завершится ошибкой.")
            .setNegativeButton("Отмена",null).setPositiveButton("Выбрать ZIP",(d,w) -> picker()).show();
        else picker();
    }
    private void picker() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT); i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*"); startActivityForResult(i,PICK_PROFILE);
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if (request != PICK_PROFILE || result != RESULT_OK || data == null || data.getData() == null) return;
        importing = true; controls(false,false); profileStatus.setText("Проверка и импорт…");
        Uri uri = data.getData();
        new Thread(() -> {
            String message;
            try (InputStream in = getContentResolver().openInputStream(uri)) {
                if (in == null) throw new IOException("Файл недоступен");
                message = ProfileImporter.importZip(in,getFilesDir());
            } catch (Exception e) { message = "Импорт отклонён: " + e.getMessage(); }
            final String answer = message;
            runOnUiThread(() -> { importing=false; profileStatus.setText(answer); controls(engine.running(),false); });
        },"acci-import").start();
    }
    private void showLog() {
        String value = engine.tail();
        if (value.isEmpty()) {
            try { value = new String(java.nio.file.Files.readAllBytes(new File(getFilesDir(),"engine.log").toPath()),StandardCharsets.UTF_8); }
            catch (IOException ignored) {}
        }
        if (value.isEmpty()) value = "Движок ещё не создавал журнал.";
        if (value.length()>12000) value=value.substring(value.length()-12000);
        TextView body = text(value,14,FG,false); body.setTypeface(Typeface.MONOSPACE);
        body.setTextIsSelectable(true); body.setPadding(dp(16),dp(16),dp(16),dp(16));
        ScrollView scroller = new ScrollView(this); scroller.setBackgroundColor(BG); scroller.addView(body);
        new AlertDialog.Builder(this).setTitle("Журнал QEMU / UART").setView(scroller)
            .setPositiveButton("Закрыть",null).show();
    }
    private void showLicenses() {
        String value;
        try (InputStream in = getAssets().open("generated/licenses.txt");
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] b = new byte[8192]; int n;
            while ((n=in.read(b))!=-1) {
                if (out.size()+n>500000) throw new IOException("License file too large");
                out.write(b,0,n);
            }
            value = new String(out.toByteArray(),StandardCharsets.UTF_8);
        } catch (IOException e) { value = "Не удалось прочитать лицензии: " + e.getMessage(); }
        TextView body = text(value,14,FG,false); body.setPadding(dp(16),dp(16),dp(16),dp(16));
        body.setTextIsSelectable(true);
        ScrollView scroller = new ScrollView(this); scroller.setBackgroundColor(BG); scroller.addView(body);
        new AlertDialog.Builder(this).setTitle("Лицензии и исходники").setView(scroller)
            .setPositiveButton("Закрыть",null).show();
    }
    @Override protected void onStop() { engine.stop("Приложение свёрнуто"); super.onStop(); }
    @Override protected void onDestroy() { engine.dispose(); super.onDestroy(); }
}