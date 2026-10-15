package dev.acci.demo;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        TextView view = new TextView(this);
        view.setText(getString(R.string.app_name) + ": 6 x 7 = " + Calc.mul(6, 7));
        view.setTextSize(24f);
        setContentView(view);
    }
}
