package dev.acci.legacyvm;

import android.content.Context;
import android.graphics.*;
import android.view.*;

public final class GuestView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
    private final RectF destination = new RectF();
    private Bitmap frame;
    private EngineController controller;
    private long lastMove;
    public GuestView(Context context) {
        super(context); setFocusable(true);
        setContentDescription("Экран гостевой системы. Коснитесь для ввода.");
    }
    public void controller(EngineController controller) { this.controller = controller; }
    public void frame(int width, int height, int[] pixels) {
        Bitmap next = Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888);
        frame = next; invalidate();
    }
    public void clear() { frame = null; invalidate(); }
    @Override protected void onMeasure(int w, int h) {
        int width = MeasureSpec.getSize(w);
        int maximum = Math.round(320 * getResources().getDisplayMetrics().density);
        setMeasuredDimension(width, Math.min(maximum, Math.round(width * 0.75f)));
    }
    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(Color.rgb(13, 17, 23));
        if (frame == null) {
            paint.setColor(Color.rgb(230, 237, 243)); paint.setTextAlign(Paint.Align.CENTER);
            paint.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
            paint.setTextSize(16 * getResources().getDisplayMetrics().scaledDensity);
            canvas.drawText("Экран гостевой системы", getWidth()/2f, getHeight()/2f - 4, paint);
            paint.setColor(Color.rgb(145, 157, 173));
            paint.setTextSize(14 * getResources().getDisplayMetrics().scaledDensity);
            canvas.drawText("Появится после запуска", getWidth()/2f, getHeight()/2f + 28, paint);
            return;
        }
        float scale = Math.min((float)getWidth()/frame.getWidth(), (float)getHeight()/frame.getHeight());
        float w = frame.getWidth()*scale, h = frame.getHeight()*scale;
        destination.set((getWidth()-w)/2, (getHeight()-h)/2, (getWidth()+w)/2, (getHeight()+h)/2);
        canvas.drawBitmap(frame, null, destination, paint);
    }
    @Override public boolean onTouchEvent(MotionEvent e) {
        if (frame == null || controller == null || destination.width() == 0) return super.onTouchEvent(e);
        int action = e.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN) getParent().requestDisallowInterceptTouchEvent(true);
        if (action == MotionEvent.ACTION_MOVE && e.getEventTime() - lastMove < 40) return true;
        lastMove = e.getEventTime();
        int x = (int)((e.getX()-destination.left)*frame.getWidth()/destination.width());
        int y = (int)((e.getY()-destination.top)*frame.getHeight()/destination.height());
        controller.pointer(x, y, action != MotionEvent.ACTION_UP && action != MotionEvent.ACTION_CANCEL);
        if (action == MotionEvent.ACTION_UP) { performClick(); getParent().requestDisallowInterceptTouchEvent(false); }
        return true;
    }
    @Override public boolean performClick() { super.performClick(); return true; }
}