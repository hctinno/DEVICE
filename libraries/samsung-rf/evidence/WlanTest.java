package com.sec.android.app.wlantest;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Parcel;
import android.os.PowerManager;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.os.SystemProperties;
import android.os.SystemService;
import android.provider.Settings;
import android.text.TextUtils;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.RelativeLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.SpinnerAdapter;
import android.widget.TextView;
import android.widget.Toast;
import com.android.internal.annotations.VisibleForTesting;
import com.samsung.android.wifi.SemWifiManager;
import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;

/* JADX INFO: loaded from: classes.dex */
public class WlanTest extends Activity {
    RelativeLayout absRxTest;
    RelativeLayout absTxTest;
    Spinner antennaRx;
    Spinner antennaTx;
    EditText backoffpower;
    Spinner bandRx;
    Spinner bandTx;
    Spinner bandwidthRx;
    Spinner bandwidthTx;
    Spinner bsscolorRx;
    Button btClearRx;
    Button btStartGetRxIqest_2G;
    Button btStartGetRxIqest_5G;
    Button btStartGetRxIqest_6E;
    Button btStartRx;
    Button btStartTx;
    Button btStopRx;
    Button btStopTx;
    EditText burst;
    TextView burstTextView;
    Spinner channelRx;
    Spinner channelTx;
    Spinner channelencodingRx;
    Spinner channelencodingTx;
    Button core0;
    Button core1;
    EditText error;
    private LinearLayout layoutAtCommands;
    LinearLayout linRxIqest;
    LinearLayout linStatus;
    private CommandHandler mCommandHandler;
    private DriverHandler mDriverHandler;
    private float mFarValue;
    private FWMode mFirmware;
    private EditText mInputCmd;
    private boolean mIsActive;
    private boolean mIsClose;
    private Sensor mProxSensor;
    private boolean mRecoveryAutoHotspotMode;
    private boolean mRecoveryBleScanMode;
    private ScrollView mScrollView;
    private ScrollView mScrollViewRxIqest;
    private SemWifiManager mSemWifiManager;
    private Button mSendCmd;
    private SensorManager mSensorManager;
    private TextView mTasMode;
    private LinearLayout mTasModeView;
    private TextView mTextView;
    TextView mTextViewRxIqestStatus;
    private IBinder mWLService;
    private WifiManager mWifiManager;
    Spinner ofdmaRx;
    Spinner ofdmaTx;
    Spinner packetTx;
    EditText payload;
    TextView payloadTextView;
    EditText per;
    String posAntennaRx;
    String posBandRx;
    String posBandTx;
    String posBandwidthRx;
    String posBandwidthTx;
    String posBssColorRx;
    String posBurstTx;
    String posChannelRx;
    String posChannelTx;
    String posChannelencodingRx;
    String posChannelencodingTx;
    String posOfdmaRx;
    String posOfdmaTx;
    String posPacketTx;
    String posPayloadTx;
    String posPower;
    String posPreambleTx;
    String posResourceunitRx;
    String posResourceunitTx;
    String posRxRuRate;
    String posTxRate;
    Spinner power;
    Spinner preamble;
    EditText received;
    Spinner resourceunitRx;
    Spinner resourceunitTx;
    Spinner rxRuRate;
    private PowerManager.WakeLock sWakeLock;
    Button start;
    Button stop;
    private String testType;
    Spinner txRate;
    String valuebackoffpower;
    boolean isBtTest = false;
    boolean is24G = true;
    private IntentFilter mIntentFilter = null;
    private final BluetoothAdapter mBluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
    private int mPosition = 0;
    private long txWaitTime = 4000;
    private long rxWaitTime = 1000;
    private boolean isTxTestPassed = false;
    private boolean sprdwlan = false;
    private boolean mtkwlan = false;
    private boolean brcmwlan = false;
    private boolean brcm4389wlan = false;
    private boolean qca6391wlan = false;
    private boolean wcn6850wlan = false;
    private boolean wcn78xxwlan = false;
    private boolean lsibtcableless = false;
    private boolean wcn6750wlan = false;
    private boolean wcn39xxwlan = false;
    private boolean needTxWaitTime = false;
    private int scanCount = 4;
    private int maxReq = 1;
    private boolean StopByCloseDUT = false;
    private boolean isFinishOnPause = false;
    private boolean isBTOff = false;
    private boolean networkScorerStatus = false;
    private boolean isManual = false;
    private String griData = "NG";
    String posAntennaTx = "0";
    String driverStatus = null;
    private boolean mIsScreenOn = true;
    private String mBufferedResultMessage = "";
    private int mDriverUnloadCmdId = -1;
    private String mDriverUnloadResult = "";
    Handler myGUIUpdateHandler = new Handler() { // from class: com.sec.android.app.wlantest.WlanTest.1
        @Override // android.os.Handler
        public void handleMessage(Message message) {
            if (message.what == 257) {
                String str = (String) message.obj;
                Log.d("WlanTest", "Inside Handle Message: EVENT_GUI_UPDATE");
                if (WlanTest.this.mTextView != null) {
                    WlanTest.this.mTextView.append(str);
                    WlanTest.this.mScrollView.scrollTo(0, WlanTest.this.mTextView.getHeight());
                    return;
                }
                return;
            }
            super.handleMessage(message);
        }
    };
    Handler myRxIqestGUIUpdateHandler = new Handler() { // from class: com.sec.android.app.wlantest.WlanTest.2
        @Override // android.os.Handler
        public void handleMessage(Message message) {
            if (message.what == 257) {
                String strReplaceAll = ((String) message.obj).replaceAll(",A1", "\nCh").replaceAll(",A2.,", " / ").replaceAll(",A2..,", " / ").replaceAll(",A2...,", " / ");
                Log.d("WlanTest", "Inside RxIqest Handle Message: EVENT_GUI_UPDATE");
                TextView textView = WlanTest.this.mTextViewRxIqestStatus;
                if (textView != null) {
                    textView.append(strReplaceAll);
                    WlanTest.this.mScrollViewRxIqest.scrollTo(0, WlanTest.this.mTextViewRxIqestStatus.getHeight());
                    return;
                }
                return;
            }
            super.handleMessage(message);
        }
    };
    private final BroadcastReceiver mReceiver = new BroadcastReceiver() { // from class: com.sec.android.app.wlantest.WlanTest.3
        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            Log.d("WlanTest", "In mReceiver getAction : " + action);
            Log.d("WlanTest", "SEC_CMDID = " + intent.getStringExtra("CMDID"));
            Log.d("WlanTest", "S_DATA = " + intent.getStringExtra("S_DATA"));
            Log.d("WlanTest", "BYPASS = " + intent.getIntExtra("BYPASS", 0));
            if (action.equals("com.sec.android.app.wlantest.WIFI_TEST_INDICATION")) {
                CommandArgs commandArgs = new CommandArgs();
                commandArgs.cmdId = intent.getIntExtra("CMDID", -1);
                commandArgs.data = intent.getStringExtra("S_DATA");
                commandArgs.bypass = intent.getIntExtra("BYPASS", 0) == 1;
                Log.i("WlanTest", "Command ID <" + commandArgs.cmdId + ">, Command Data<" + commandArgs.data + "> ");
                Message message = new Message();
                message.what = 262;
                message.obj = commandArgs;
                WlanTest.this.mCommandHandler.sendMessage(message);
            }
        }
    };
    private final SensorEventListener mListener = new SensorEventListener() { // from class: com.sec.android.app.wlantest.WlanTest.37
        @Override // android.hardware.SensorEventListener
        public void onAccuracyChanged(Sensor sensor, int i) {
            Log.d("WlanTest", "Processing onAccuracyChanged event at : " + System.currentTimeMillis());
        }

        @Override // android.hardware.SensorEventListener
        public void onSensorChanged(SensorEvent sensorEvent) throws Throwable {
            if (sensorEvent.sensor.getType() == 8) {
                WlanTest wlanTest = WlanTest.this;
                wlanTest.mIsClose = sensorEvent.values[0] < wlanTest.mFarValue;
                Log.d("WlanTest", "Processing onSensorChanged event at : " + System.currentTimeMillis() + " , mIsClose : " + WlanTest.this.mIsClose);
                if (WlanTest.this.mIsClose) {
                    Log.d("WlanTest", "Detect something be close ~~ ");
                    WlanTest wlanTest2 = WlanTest.this;
                    wlanTest2.backoffpower = (EditText) wlanTest2.findViewById(R.id.backoffpower);
                    WlanTest wlanTest3 = WlanTest.this;
                    wlanTest3.valuebackoffpower = wlanTest3.backoffpower.getText().toString();
                    if (WlanTest.this.btStartTx.isEnabled()) {
                        return;
                    }
                    WlanTest wlanTest4 = WlanTest.this;
                    wlanTest4.dutCommand(7, wlanTest4.valuebackoffpower);
                    return;
                }
                Log.d("WlanTest", "Nothing be close");
                if (WlanTest.this.btStartTx.isEnabled()) {
                    return;
                }
                WlanTest wlanTest5 = WlanTest.this;
                wlanTest5.dutCommand(7, wlanTest5.posPower);
            }
        }
    };

    protected static final class CommandArgs {
        public boolean bypass;
        public int cmdId = 100;
        public String data = "";
    }

    private enum FWMode {
        NotSet,
        TestMode,
        NormalMode
    }

    @VisibleForTesting
    BroadcastReceiver getBroadcastReceiver() {
        return this.mReceiver;
    }

    /* JADX WARN: Code duplicated, block: B:16:0x013f  */
    @Override // android.app.Activity
    public void onCreate(Bundle bundle) {
        boolean zEquals;
        BluetoothAdapter bluetoothAdapter;
        super.onCreate(bundle);
        Log.d("WlanTest", "on create");
        setContentView(R.layout.main);
        SensorManager sensorManager = (SensorManager) getSystemService("sensor");
        this.mSensorManager = sensorManager;
        Sensor defaultSensor = sensorManager.getDefaultSensor(8);
        this.mProxSensor = defaultSensor;
        this.mFarValue = defaultSensor != null ? defaultSensor.getMaximumRange() : 0.0f;
        Log.e("WlanTest", "Mode : " + getIntent().getExtra("MODE"));
        IntentFilter intentFilter = new IntentFilter();
        this.mIntentFilter = intentFilter;
        intentFilter.addAction("com.sec.android.app.wlantest.WIFI_TEST_INDICATION");
        this.mTextView = (TextView) findViewById(R.id.status);
        this.mScrollView = (ScrollView) findViewById(R.id.ScrollView1);
        PowerManager.WakeLock wakeLockNewWakeLock = ((PowerManager) getSystemService("power")).newWakeLock(536870922, "WlanTest");
        this.sWakeLock = wakeLockNewWakeLock;
        wakeLockNewWakeLock.acquire();
        this.mFirmware = FWMode.NotSet;
        this.mWifiManager = (WifiManager) getSystemService("wifi");
        this.mSemWifiManager = (SemWifiManager) getSystemService("sem_wifi");
        HandlerThread handlerThread = new HandlerThread("Driver Handler Thread");
        handlerThread.start();
        this.mDriverHandler = new DriverHandler(handlerThread.getLooper());
        HandlerThread handlerThread2 = new HandlerThread("Command Handler Thread");
        handlerThread2.start();
        this.mCommandHandler = new CommandHandler(handlerThread2.getLooper());
        Log.d("WlanTest", "In onCreate...Registering main Receiver[mReceiver]!!!");
        registerReceiver(this.mReceiver, this.mIntentFilter, 2);
        SystemProperties.set("sys.factory.wlantest.running", "1");
        boolean zIsWifiEnabled = this.mWifiManager.isWifiEnabled();
        boolean zIsScanAlwaysAvailable = this.mWifiManager.isScanAlwaysAvailable();
        boolean zIsWifiApEnabled = this.mWifiManager.isWifiApEnabled();
        boolean z = Settings.Global.getInt(getContentResolver(), "airplane_mode_on", 0) != 0;
        Log.e("WlanTest", "...isNormalDriverLoaded : " + zIsWifiEnabled);
        Log.e("WlanTest", "...isApDriverLoaded : " + zIsWifiApEnabled);
        if (!zIsScanAlwaysAvailable || z) {
            zEquals = true;
        } else {
            this.mWifiManager.setScanAlwaysAvailable(false);
            if (this.mWifiManager.getWifiState() == 1) {
                zEquals = "OK".equals(checkDriverResult("wlan.driver.status", "unloaded", 5));
            } else {
                zEquals = true;
            }
        }
        if (Settings.Global.getInt(getContentResolver(), "sem_wifi_network_rating_scorer_enabled_labs", 0) == 1) {
            this.networkScorerStatus = true;
            Settings.Global.putInt(getContentResolver(), "sem_wifi_network_rating_scorer_enabled_labs", 0);
        }
        if (zIsWifiApEnabled) {
            Log.e("WlanTest", "...WiFi AP Driver already loaded!!!Removing the Drivers!!");
            Message message = new Message();
            message.what = 257;
            message.obj = "\nUnloading AP Driver and Loading Mfg Driver\n";
            this.myGUIUpdateHandler.sendMessage(message);
            this.mWifiManager.stopSoftAp();
            if (zIsWifiEnabled) {
                int i = 50;
                while (true) {
                    int i2 = i - 1;
                    if (i <= 0) {
                        break;
                    }
                    if (!this.mWifiManager.isWifiApEnabled()) {
                        Log.e("WlanTest", "SoftAp Disabled!");
                        break;
                    }
                    if (i2 == 0) {
                        Message message2 = new Message();
                        message2.what = 257;
                        message2.obj = "\nFail to Disable Softap\nPlease retry!\n";
                        this.myGUIUpdateHandler.sendMessage(message2);
                    }
                    try {
                        Thread.sleep(100L);
                    } catch (InterruptedException unused) {
                    }
                    i = i2;
                }
            } else {
                zEquals = "OK".equals(checkDriverResult("wlan.driver.status", "unloaded", 5));
            }
        }
        if (zIsWifiEnabled) {
            Log.e("WlanTest", "...WiFi Driver already loaded!!!Removing the Drivers!!");
            Message message3 = new Message();
            message3.what = 257;
            message3.obj = "\nUnloading Normal Driver and Loading Mfg Driver\n";
            this.myGUIUpdateHandler.sendMessage(message3);
            this.mWifiManager.setWifiEnabled(false);
            zEquals = "OK".equals(checkDriverResult("wlan.driver.status", "unloaded", 5));
        }
        this.mTasModeView = (LinearLayout) findViewById(R.id.tasmodeview);
        TextView textView = (TextView) findViewById(R.id.tasmode);
        this.mTasMode = textView;
        textView.setText(tasModeToString(getTasMode()));
        WlanFeatureChecker wlanFeatureChecker = new WlanFeatureChecker(getWifiSupportedFeatureSet());
        Log.d("WlanTest", "isWifi6Supported " + wlanFeatureChecker.isWifi6Supported() + "\n isWifi6ESupported " + wlanFeatureChecker.isWifi6ESupported() + "\n isWifi7Supported " + wlanFeatureChecker.isWifi7Supported());
        if (!SystemProperties.get("init.svc.wlandutservice").equals("running")) {
            Log.e("WlanTest", "...Start wlandutservice !!!");
            startService("wlandutservice");
        } else {
            Log.e("WlanTest", "...wlservice is already started!!!");
        }
        int i3 = 50;
        while (true) {
            int i4 = i3 - 1;
            if (i3 <= 0) {
                break;
            }
            String str = SystemProperties.get("init.svc.wlandutservice");
            Log.e("WlanTest", "init.svc.wlandutservice : " + str);
            if (str.equals("running")) {
                IBinder service = ServiceManager.getService("WlanDutService");
                this.mWLService = service;
                if (service != null) {
                    Log.i("WlanTest", "get WlanDutService successfully");
                    break;
                }
                Log.e("WlanTest", "fail to get WlanDutService but we will try more!");
            }
            if (i4 == 0) {
                Message message4 = new Message();
                message4.what = 257;
                message4.obj = "\nFail to Launch wlandutservice\nPlease retry!\n";
                this.myGUIUpdateHandler.sendMessage(message4);
            }
            try {
                Thread.sleep(100L);
            } catch (InterruptedException unused2) {
            }
            Log.e("WlanTest", "tryCount : " + i4);
            i3 = i4;
        }
        setVendorProperty("vendor.wlandriver.status", "unloaded");
        Intent intent = new Intent("android.intent.action.WIFI_DRIVER_INDICATION");
        intent.putExtra("STATUS", "ready");
        intent.setPackage("com.sec.facatfunction");
        sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
        Log.i("WlanTest", "onCreate: Sent response intent: STATUS: ready");
        if (getIntent().getExtra("MODE") == null) {
            Log.e("WlanTest", " Mode is : " + getIntent().getExtra("MODE"));
        } else {
            this.isManual = getIntent().getExtra("MODE").equals("manual");
        }
        if (zEquals) {
            try {
                if (this.isManual) {
                    Message message5 = new Message();
                    message5.what = 258;
                    message5.obj = "test";
                    setVendorProperty("vendor.wlandriver.mode", "test");
                    this.mDriverHandler.sendMessage(message5);
                }
            } catch (NullPointerException unused3) {
                Log.e("WlanTest", "Ignore NullPointerException for check Launcher");
                Message message6 = new Message();
                message6.what = 258;
                message6.obj = "test";
                setVendorProperty("vendor.wlandriver.mode", "test");
                this.mDriverHandler.sendMessage(message6);
            }
        }
        Toast.makeText(this, "Driver loading started\nPlease wait till status is shown", 1).show();
        Log.d("WlanTest", "In onCreate...Registering ItemSelectedListeners!!!");
        this.linStatus = (LinearLayout) findViewById(R.id.main_page);
        this.absTxTest = (RelativeLayout) findViewById(R.id.tx_test);
        this.absRxTest = (RelativeLayout) findViewById(R.id.rx_test);
        initAtCommandsView();
        this.channelRx = (Spinner) findViewById(R.id.channelRx);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource = ArrayAdapter.createFromResource(this, R.array.channel, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource2 = ArrayAdapter.createFromResource(this, R.array.channel5G, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource2.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final int[] intArray = getResources().getIntArray(R.array.channel5G_Value);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource3 = ArrayAdapter.createFromResource(this, R.array.channel6G, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource3.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final int[] intArray2 = getResources().getIntArray(R.array.channel6G_Value);
        ((TextView) findViewById(R.id.bandwidthRx_tv)).setVisibility(0);
        Spinner spinner = (Spinner) findViewById(R.id.bandwidthRx);
        this.bandwidthRx = spinner;
        spinner.setVisibility(0);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource4 = ArrayAdapter.createFromResource(this, R.array.bandwidth_be, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource4.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource5 = ArrayAdapter.createFromResource(this, R.array.bandwidthScanCore, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource5.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.channelRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.4
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                Log.d("WlanTest", "...." + WlanTest.this.posChannelRx);
                boolean zEquals2 = WlanTest.this.posBandRx.equals("1");
                WlanTest wlanTest = WlanTest.this;
                if (zEquals2) {
                    wlanTest.posChannelRx = Integer.toString(i5 + 1);
                    WlanTest.this.bandwidthRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource4);
                    Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                } else {
                    boolean zEquals3 = wlanTest.posBandRx.equals("2");
                    WlanTest wlanTest2 = WlanTest.this;
                    if (zEquals3) {
                        wlanTest2.posChannelRx = Integer.toString(intArray[i5]);
                        WlanTest.this.bandwidthRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource4);
                        Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                    } else {
                        boolean zEquals4 = wlanTest2.posBandRx.equals("3");
                        WlanTest wlanTest3 = WlanTest.this;
                        if (zEquals4) {
                            wlanTest3.posChannelRx = Integer.toString(intArray2[i5]);
                            WlanTest.this.bandwidthRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource4);
                            Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                        } else {
                            boolean zEquals5 = wlanTest3.posBandRx.equals("4");
                            WlanTest wlanTest4 = WlanTest.this;
                            if (zEquals5) {
                                wlanTest4.posChannelRx = Integer.toString(i5 + 1);
                                WlanTest.this.bandwidthRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource5);
                                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                            } else if (wlanTest4.posBandRx.equals("5")) {
                                WlanTest.this.posChannelRx = Integer.toString(intArray[i5]);
                                WlanTest.this.bandwidthRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource5);
                                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                            } else {
                                Log.d("WlanTest", "position is not set");
                            }
                        }
                    }
                }
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.bandRx = (Spinner) findViewById(R.id.bandRx);
        ArrayList arrayList = new ArrayList();
        arrayList.add("2.4GHz");
        arrayList.add("5GHz");
        arrayList.add("6GHz");
        arrayList.add("2.4GHz Scan Core");
        arrayList.add("5GHz Scan Core");
        ArrayAdapter arrayAdapter = new ArrayAdapter(this, android.R.layout.simple_spinner_item, arrayList);
        arrayAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.bandRx.setAdapter((SpinnerAdapter) arrayAdapter);
        this.bandRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.5
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                String string = adapterView.getSelectedItem().toString();
                Log.d("WlanTest", "...." + i5 + string);
                if ("2.4GHz".equals(string)) {
                    WlanTest wlanTest = WlanTest.this;
                    wlanTest.posBandRx = "1";
                    wlanTest.channelRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource);
                    return;
                }
                if ("5GHz".equals(string)) {
                    WlanTest wlanTest2 = WlanTest.this;
                    wlanTest2.posBandRx = "2";
                    wlanTest2.channelRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource2);
                    return;
                }
                if ("6GHz".equals(string)) {
                    WlanTest wlanTest3 = WlanTest.this;
                    wlanTest3.posBandRx = "3";
                    wlanTest3.channelRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource3);
                } else if ("2.4GHz Scan Core".equals(string)) {
                    WlanTest wlanTest4 = WlanTest.this;
                    wlanTest4.posBandRx = "4";
                    wlanTest4.channelRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource);
                } else {
                    if ("5GHz Scan Core".equals(string)) {
                        WlanTest wlanTest5 = WlanTest.this;
                        wlanTest5.posBandRx = "5";
                        wlanTest5.channelRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource2);
                        return;
                    }
                    Log.d("WlanTest", "Band selection failed!!");
                }
            }
        });
        ((TextView) findViewById(R.id.antennaRx_tv)).setVisibility(0);
        Spinner spinner2 = (Spinner) findViewById(R.id.antennaRx);
        this.antennaRx = spinner2;
        spinner2.setVisibility(0);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource6 = ArrayAdapter.createFromResource(this, R.array.antenna, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource6.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.antennaRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource6);
        this.antennaRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.6
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posAntennaRx = Integer.toString(i5);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.bsscolorRx = (Spinner) findViewById(R.id.bsscolorRx);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource7 = ArrayAdapter.createFromResource(this, R.array.bsscolor, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource7.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.bsscolorRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource7);
        this.bsscolorRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.7
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posBssColorRx = Integer.toString(i5);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.resourceunitRx = (Spinner) findViewById(R.id.resourceunitRx);
        ArrayAdapter.createFromResource(this, R.array.none, android.R.layout.simple_spinner_item).setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        ArrayAdapter.createFromResource(this, R.array.resourceunit_ax, android.R.layout.simple_spinner_item).setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource8 = ArrayAdapter.createFromResource(this, R.array.resourceunit_be, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource8.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.resourceunitRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource8);
        this.resourceunitRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.8
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posResourceunitRx = adapterView.getItemAtPosition(i5).toString();
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.rxRuRate = (Spinner) findViewById(R.id.rxRuRate);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource9 = ArrayAdapter.createFromResource(this, R.array.rxRuRate, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource9.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.rxRuRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource9);
        this.rxRuRate.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.9
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posRxRuRate = Integer.toString(i5 + 15);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        ((TextView) findViewById(R.id.channelencodingRx_tv)).setVisibility(0);
        Spinner spinner3 = (Spinner) findViewById(R.id.channelencodingRx);
        this.channelencodingRx = spinner3;
        spinner3.setVisibility(0);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource10 = ArrayAdapter.createFromResource(this, R.array.channelencoding, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource10.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.channelencodingRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource10);
        this.channelencodingRx.setSelection(1);
        this.channelencodingRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.10
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posChannelencodingRx = Integer.toString(i5);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        ((TextView) findViewById(R.id.ofdmaRx_tv)).setVisibility(0);
        Spinner spinner4 = (Spinner) findViewById(R.id.ofdmaRx);
        this.ofdmaRx = spinner4;
        spinner4.setVisibility(0);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource11 = ArrayAdapter.createFromResource(this, R.array.ofdma, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource11.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.ofdmaRx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource11);
        this.ofdmaRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.11
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posOfdmaRx = Integer.toString(i5);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                if (i5 == 1) {
                    ((TextView) WlanTest.this.findViewById(R.id.bsscolorRx_tv)).setVisibility(0);
                    WlanTest.this.bsscolorRx.setVisibility(0);
                    ((TextView) WlanTest.this.findViewById(R.id.resourceunitRx_tv)).setVisibility(0);
                    WlanTest.this.resourceunitRx.setVisibility(0);
                    ((TextView) WlanTest.this.findViewById(R.id.rxRuRate_tv)).setVisibility(0);
                    WlanTest.this.rxRuRate.setVisibility(0);
                    return;
                }
                WlanTest wlanTest = WlanTest.this;
                if (i5 == 2) {
                    ((TextView) wlanTest.findViewById(R.id.bsscolorRx_tv)).setVisibility(8);
                    WlanTest.this.bsscolorRx.setVisibility(8);
                    ((TextView) WlanTest.this.findViewById(R.id.resourceunitRx_tv)).setVisibility(0);
                    WlanTest.this.resourceunitRx.setVisibility(0);
                    ((TextView) WlanTest.this.findViewById(R.id.rxRuRate_tv)).setVisibility(8);
                    WlanTest.this.rxRuRate.setVisibility(8);
                    return;
                }
                ((TextView) wlanTest.findViewById(R.id.bsscolorRx_tv)).setVisibility(8);
                WlanTest.this.bsscolorRx.setVisibility(8);
                ((TextView) WlanTest.this.findViewById(R.id.resourceunitRx_tv)).setVisibility(8);
                WlanTest.this.resourceunitRx.setVisibility(8);
                ((TextView) WlanTest.this.findViewById(R.id.rxRuRate_tv)).setVisibility(8);
                WlanTest.this.rxRuRate.setVisibility(8);
            }
        });
        this.bandwidthRx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.12
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posBandwidthRx = Integer.toString(i5 + 1);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.packetTx = (Spinner) findViewById(R.id.packetTx);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource12 = ArrayAdapter.createFromResource(this, R.array.packetTx, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource12.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.packetTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource12);
        this.packetTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.13
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posPacketTx = Integer.toString(i5 + 1);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.channelTx = (Spinner) findViewById(R.id.channelTx);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource13 = ArrayAdapter.createFromResource(this, R.array.channel, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource13.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource14 = ArrayAdapter.createFromResource(this, R.array.channel5G, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource14.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource15 = ArrayAdapter.createFromResource(this, R.array.channel6G, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource15.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final int[] intArray3 = getResources().getIntArray(R.array.channel5G_Value);
        final int[] intArray4 = getResources().getIntArray(R.array.channel6G_Value);
        this.bandwidthTx = (Spinner) findViewById(R.id.bandwidthTx);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource16 = ArrayAdapter.createFromResource(this, R.array.bandwidth_be, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource16.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.channelTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.14
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                Log.d("WlanTest", "...." + WlanTest.this.posChannelTx);
                boolean zEquals2 = WlanTest.this.posBandTx.equals("1");
                WlanTest wlanTest = WlanTest.this;
                if (zEquals2) {
                    wlanTest.posChannelTx = Integer.toString(i5 + 1);
                    Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                    WlanTest.this.bandwidthTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource16);
                } else {
                    boolean zEquals3 = wlanTest.posBandTx.equals("2");
                    WlanTest wlanTest2 = WlanTest.this;
                    if (zEquals3) {
                        wlanTest2.posChannelTx = Integer.toString(intArray3[i5]);
                        Log.e("WlanTest", "posChannelTx " + WlanTest.this.posChannelTx);
                        Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                        WlanTest.this.bandwidthTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource16);
                    } else if (wlanTest2.posBandTx.equals("3")) {
                        WlanTest.this.posChannelTx = Integer.toString(intArray4[i5]);
                        Log.e("WlanTest", "posChannelTx " + WlanTest.this.posChannelTx);
                        Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                        WlanTest.this.bandwidthTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource16);
                    } else {
                        Log.d("WlanTest", "position is not set");
                    }
                }
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.txRate = (Spinner) findViewById(R.id.txRate);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource17 = ArrayAdapter.createFromResource(this, R.array.txRate_be, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource17.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource18 = ArrayAdapter.createFromResource(this, R.array.txRate5G_be, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource18.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource19 = ArrayAdapter.createFromResource(this, R.array.MIMORate, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource19.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource20 = ArrayAdapter.createFromResource(this, R.array.MIMORate5G, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource20.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        final ArrayAdapter<CharSequence> arrayAdapterCreateFromResource21 = ArrayAdapter.createFromResource(this, R.array.txRate5G_be, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource21.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.txRate.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.15
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                boolean zEquals2 = WlanTest.this.posBandTx.equals("1");
                WlanTest wlanTest = WlanTest.this;
                if (zEquals2) {
                    wlanTest.posTxRate = Integer.toString(i5 + 1);
                    Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                    return;
                }
                boolean zEquals3 = wlanTest.posBandTx.equals("2");
                WlanTest wlanTest2 = WlanTest.this;
                if (zEquals3) {
                    wlanTest2.posTxRate = Integer.toString(i5 + 4);
                    Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                    return;
                }
                if (wlanTest2.posBandTx.equals("3")) {
                    WlanTest.this.posTxRate = Integer.toString(i5 + 4);
                    Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                    return;
                }
                Log.d("WlanTest", "position is not set");
            }
        });
        this.power = (Spinner) findViewById(R.id.power);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource22 = ArrayAdapter.createFromResource(this, R.array.power_11ax, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource22.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.power.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource22);
        this.power.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.16
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posPower = Float.toString((i5 - 20.0f) / 2.0f);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.bandTx = (Spinner) findViewById(R.id.bandTx);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource23 = ArrayAdapter.createFromResource(this, R.array.bandTx, android.R.layout.simple_spinner_item);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource24 = ArrayAdapter.createFromResource(this, R.array.bandTx6G, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource23.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        arrayAdapterCreateFromResource24.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.bandTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource24);
        this.bandTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.17
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.mPosition = i5;
                WlanTest.this.posBandTx = Integer.toString(i5 + 1);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                if (i5 == 0) {
                    boolean zEquals2 = WlanTest.this.posAntennaTx.equals("0");
                    WlanTest wlanTest = WlanTest.this;
                    if (zEquals2) {
                        wlanTest.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource13);
                        WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource19);
                    } else {
                        wlanTest.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource13);
                        WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource17);
                    }
                    WlanTest.this.core0.setEnabled(true);
                    WlanTest.this.core1.setEnabled(false);
                } else if (1 == i5) {
                    boolean zEquals3 = WlanTest.this.posAntennaTx.equals("0");
                    WlanTest wlanTest2 = WlanTest.this;
                    if (zEquals3) {
                        wlanTest2.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource14);
                        WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource20);
                    } else {
                        wlanTest2.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource14);
                        WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource18);
                    }
                    WlanTest.this.core0.setEnabled(false);
                    WlanTest.this.core1.setEnabled(true);
                } else if (2 == i5) {
                    WlanTest.this.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource15);
                    WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource21);
                    WlanTest.this.core0.setEnabled(false);
                    WlanTest.this.core1.setEnabled(true);
                }
                WlanTest.this.is24G = i5 == 0;
            }
        });
        ((TextView) findViewById(R.id.channelencoding_tv)).setVisibility(0);
        Spinner spinner5 = (Spinner) findViewById(R.id.channelencodingTx);
        this.channelencodingTx = spinner5;
        spinner5.setVisibility(0);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource25 = ArrayAdapter.createFromResource(this, R.array.channelencoding, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource25.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.channelencodingTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource25);
        this.channelencodingTx.setSelection(1);
        this.channelencodingTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.18
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posChannelencodingTx = Integer.toString(i5);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.resourceunitTx = (Spinner) findViewById(R.id.resourceunitTx);
        ArrayAdapter.createFromResource(this, R.array.none, android.R.layout.simple_spinner_item).setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        ArrayAdapter.createFromResource(this, R.array.resourceunit_ax, android.R.layout.simple_spinner_item).setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource26 = ArrayAdapter.createFromResource(this, R.array.resourceunit_be, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource26.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.resourceunitTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource26);
        this.resourceunitTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.19
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posResourceunitTx = adapterView.getItemAtPosition(i5).toString();
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        ((TextView) findViewById(R.id.ofdma_tv)).setVisibility(0);
        Spinner spinner6 = (Spinner) findViewById(R.id.ofdmaTx);
        this.ofdmaTx = spinner6;
        spinner6.setVisibility(0);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource27 = ArrayAdapter.createFromResource(this, R.array.ofdma, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource27.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.ofdmaTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource27);
        this.ofdmaTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.20
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posOfdmaTx = Integer.toString(i5);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                if (i5 == 1 || i5 == 2) {
                    ((TextView) WlanTest.this.findViewById(R.id.resourceunit_tv)).setVisibility(0);
                    WlanTest.this.resourceunitTx.setVisibility(0);
                } else {
                    ((TextView) WlanTest.this.findViewById(R.id.resourceunit_tv)).setVisibility(8);
                    WlanTest.this.resourceunitTx.setVisibility(8);
                }
            }
        });
        arrayAdapterCreateFromResource16.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.bandwidthTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.21
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posBandwidthTx = Integer.toString(i5 + 1);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                if (i5 <= 4 || Integer.parseInt(WlanTest.this.posPreambleTx) >= 4) {
                    return;
                }
                WlanTest.this.preamble.setSelection(4);
            }
        });
        ((TextView) findViewById(R.id.antenna_tv)).setVisibility(0);
        Spinner spinner7 = (Spinner) findViewById(R.id.antennaTx);
        this.antennaTx = spinner7;
        spinner7.setVisibility(0);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource28 = ArrayAdapter.createFromResource(this, R.array.antenna, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource28.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.antennaTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource28);
        this.antennaTx.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.23
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posAntennaTx = Integer.toString(i5);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
                WlanTest wlanTest = WlanTest.this;
                if (i5 == 0) {
                    boolean zEquals2 = wlanTest.posBandTx.equals("1");
                    WlanTest wlanTest2 = WlanTest.this;
                    if (!zEquals2) {
                        boolean zEquals3 = wlanTest2.posBandTx.equals("2");
                        WlanTest wlanTest3 = WlanTest.this;
                        if (zEquals3) {
                            wlanTest3.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource14);
                            WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource20);
                            return;
                        } else {
                            wlanTest3.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource15);
                            WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource21);
                            return;
                        }
                    }
                    wlanTest2.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource13);
                    WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource19);
                    return;
                }
                boolean zEquals4 = wlanTest.posBandTx.equals("1");
                WlanTest wlanTest4 = WlanTest.this;
                if (!zEquals4) {
                    boolean zEquals5 = wlanTest4.posBandTx.equals("2");
                    WlanTest wlanTest5 = WlanTest.this;
                    if (zEquals5) {
                        wlanTest5.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource14);
                        WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource18);
                        return;
                    } else {
                        wlanTest5.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource15);
                        WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource21);
                        return;
                    }
                }
                wlanTest4.channelTx.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource13);
                WlanTest.this.txRate.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource17);
            }
        });
        this.preamble = (Spinner) findViewById(R.id.preamble);
        ArrayAdapter<CharSequence> arrayAdapterCreateFromResource29 = ArrayAdapter.createFromResource(this, R.array.preamble, android.R.layout.simple_spinner_item);
        arrayAdapterCreateFromResource29.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.preamble.setAdapter((SpinnerAdapter) arrayAdapterCreateFromResource29);
        this.preamble.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.sec.android.app.wlantest.WlanTest.24
            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onNothingSelected(AdapterView<?> adapterView) {
            }

            @Override // android.widget.AdapterView.OnItemSelectedListener
            public void onItemSelected(AdapterView<?> adapterView, View view, int i5, long j) {
                WlanTest.this.posPreambleTx = Integer.toString(i5 + 1);
                Log.d("WlanTest", "...." + i5 + adapterView.getItemAtPosition(i5));
            }
        });
        this.burstTextView = (TextView) findViewById(R.id.burst_interval_tv);
        this.payloadTextView = (TextView) findViewById(R.id.payload_length_tv);
        this.burst = (EditText) findViewById(R.id.burst_edittext);
        this.payload = (EditText) findViewById(R.id.payload_edittext);
        Log.d("WlanTest", "In onCreate...Registering ClickListeners!!!");
        this.start = (Button) findViewById(R.id.btn1);
        this.stop = (Button) findViewById(R.id.btn2);
        this.start.setEnabled(true);
        this.stop.setEnabled(false);
        this.start.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.25
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                WlanTest.this.start();
                WlanTest.this.start.setEnabled(false);
                WlanTest.this.stop.setEnabled(true);
            }
        });
        this.stop.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.26
            @Override // android.view.View.OnClickListener
            public void onClick(View view) throws Throwable {
                WlanTest.this.stop();
                WlanTest.this.start.setEnabled(true);
                WlanTest.this.stop.setEnabled(false);
            }
        });
        this.core0 = (Button) findViewById(R.id.btStartCore0);
        this.core1 = (Button) findViewById(R.id.btStartCore1);
        this.core0.setVisibility(8);
        this.core1.setVisibility(8);
        this.core0.setVisibility(0);
        this.core1.setVisibility(0);
        this.core0.setEnabled(true);
        this.core1.setEnabled(false);
        this.core0.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.27
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                WlanTest.this.startRsdbTx("1");
                WlanTest.this.btStartTx.setEnabled(false);
                WlanTest.this.btStopTx.setEnabled(true);
                WlanTest.this.core0.setEnabled(false);
            }
        });
        this.core1.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.28
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                WlanTest.this.startRsdbTx("2");
                WlanTest.this.btStartTx.setEnabled(false);
                WlanTest.this.btStopTx.setEnabled(true);
                WlanTest.this.core1.setEnabled(false);
            }
        });
        this.btStartTx = (Button) findViewById(R.id.btStartTx);
        this.btStopTx = (Button) findViewById(R.id.btStopTx);
        this.btStartTx.setEnabled(true);
        this.btStopTx.setEnabled(false);
        this.btStartTx.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.29
            /* JADX WARN: Code duplicated, block: B:51:0x018c  */
            /* JADX WARN: Code duplicated, block: B:55:0x01a7  */
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                WlanTest wlanTest;
                WlanTest wlanTest2;
                Log.d("WlanTest", "  ........ in btStartTx......");
                WlanTest.this.btStartTx.setEnabled(false);
                WlanTest.this.btStopTx.setEnabled(true);
                WlanTest.this.core0.setEnabled(false);
                WlanTest.this.core1.setEnabled(false);
                WlanTest wlanTest3 = WlanTest.this;
                wlanTest3.posBurstTx = wlanTest3.burst.getText().toString();
                WlanTest wlanTest4 = WlanTest.this;
                wlanTest4.posPayloadTx = wlanTest4.payload.getText().toString();
                if (WlanTest.this.dutCommand(0, "0").equals("OK")) {
                    Log.d("WlanTest", "1.Open DUT - OK");
                    WlanTest wlanTest5 = WlanTest.this;
                    if (wlanTest5.dutCommand(16, wlanTest5.posBandTx).equals("OK")) {
                        Log.d("WlanTest", "2.Set Band - OK");
                        WlanTest wlanTest6 = WlanTest.this;
                        if (wlanTest6.dutCommand(6, wlanTest6.posChannelTx).equals("OK")) {
                            Log.d("WlanTest", "3.Set Channel - OK");
                            WlanTest wlanTest7 = WlanTest.this;
                            if (wlanTest7.dutCommand(4, wlanTest7.posAntennaTx).equals("OK")) {
                                Log.d("WlanTest", "4.Set Antenna - OK");
                                WlanTest wlanTest8 = WlanTest.this;
                                if (wlanTest8.dutCommand(2, wlanTest8.posTxRate).equals("OK")) {
                                    Log.d("WlanTest", "5.Set Data Rate - OK");
                                    WlanTest wlanTest9 = WlanTest.this;
                                    if (wlanTest9.dutCommand(5, wlanTest9.posPreambleTx).equals("OK")) {
                                        Log.d("WlanTest", "6.Set Preamble or Short Guard Interval - OK");
                                        WlanTest wlanTest10 = WlanTest.this;
                                        if (wlanTest10.dutCommand(8, wlanTest10.posBurstTx).equals("OK")) {
                                            Log.d("WlanTest", "7.Set Burst Interval - OK");
                                            WlanTest wlanTest11 = WlanTest.this;
                                            if (wlanTest11.dutCommand(9, wlanTest11.posPayloadTx).equals("OK")) {
                                                Log.d("WlanTest", "8.Set PayLoad - OK");
                                                WlanTest wlanTest12 = WlanTest.this;
                                                if (wlanTest12.dutCommand(17, wlanTest12.posBandwidthTx).equals("OK")) {
                                                    Log.d("WlanTest", "9.Set BandWidth - OK");
                                                    WlanTest wlanTest13 = WlanTest.this;
                                                    if (wlanTest13.dutCommand(26, wlanTest13.posChannelencodingTx).equals("OK")) {
                                                        Log.d("WlanTest", "10.Set Channel Encoding - OK");
                                                        boolean zEquals2 = "2".equals(WlanTest.this.posOfdmaTx);
                                                        WlanTest wlanTest14 = WlanTest.this;
                                                        if (zEquals2) {
                                                            if (wlanTest14.dutCommand(49, "1").equals("OK")) {
                                                                Log.d("WlanTest", "11.Set non-OFDMA MRU - OK");
                                                                WlanTest wlanTest15 = WlanTest.this;
                                                                if (wlanTest15.dutCommand(27, wlanTest15.posResourceunitTx).equals("OK")) {
                                                                    Log.d("WlanTest", "11.Set Resource Uint - OK");
                                                                    wlanTest = WlanTest.this;
                                                                    if (wlanTest.dutCommand(7, wlanTest.posPower).equals("OK")) {
                                                                        Log.d("WlanTest", "12.Set Tx Gain - OK");
                                                                        wlanTest2 = WlanTest.this;
                                                                        if (wlanTest2.dutCommand(10, wlanTest2.posPacketTx).equals("OK")) {
                                                                            Log.d("WlanTest", "13.Tx Start - OK");
                                                                            return;
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        } else {
                                                            if ("1".equals(wlanTest14.posOfdmaTx)) {
                                                                WlanTest wlanTest16 = WlanTest.this;
                                                                if (wlanTest16.dutCommand(27, wlanTest16.posResourceunitTx).equals("OK")) {
                                                                    Log.d("WlanTest", "11.Set Resource Uint - OK");
                                                                }
                                                            } else {
                                                                Log.d("WlanTest", "11.Set Resource Uint - not support");
                                                            }
                                                            wlanTest = WlanTest.this;
                                                            if (wlanTest.dutCommand(7, wlanTest.posPower).equals("OK")) {
                                                                Log.d("WlanTest", "12.Set Tx Gain - OK");
                                                                wlanTest2 = WlanTest.this;
                                                                if (wlanTest2.dutCommand(10, wlanTest2.posPacketTx).equals("OK")) {
                                                                    Log.d("WlanTest", "13.Tx Start - OK");
                                                                    return;
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Log.e("WlanTest", "Tx Test failed!");
            }
        });
        this.btStopTx.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.30
            /* JADX WARN: Code duplicated, block: B:13:0x005f  */
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                Log.d("WlanTest", "  ........ in btStopTx......");
                WlanTest.this.btStopTx.setEnabled(false);
                int i5 = WlanTest.this.mPosition;
                WlanTest wlanTest = WlanTest.this;
                if (i5 == 0) {
                    wlanTest.core0.setEnabled(true);
                    WlanTest.this.core1.setEnabled(false);
                } else if (wlanTest.mPosition == 1) {
                    WlanTest.this.core0.setEnabled(false);
                    WlanTest.this.core1.setEnabled(true);
                }
                if (WlanTest.this.dutCommand(11, "0").equals("OK")) {
                    Log.d("WlanTest", "1.Tx Stop - OK");
                    if (WlanTest.this.dutCommand(1, "0").equals("OK")) {
                        Log.d("WlanTest", "2.Close DUT - OK");
                    } else {
                        Log.e("WlanTest", "Tx Stop - failed");
                    }
                } else {
                    Log.e("WlanTest", "Tx Stop - failed");
                }
                WlanTest.this.btStartTx.setEnabled(true);
                int i6 = WlanTest.this.mPosition;
                WlanTest wlanTest2 = WlanTest.this;
                if (i6 == 0) {
                    wlanTest2.core0.setEnabled(true);
                    WlanTest.this.core1.setEnabled(false);
                } else if (wlanTest2.mPosition == 1) {
                    WlanTest.this.core0.setEnabled(false);
                    WlanTest.this.core1.setEnabled(true);
                }
            }
        });
        this.btStartRx = (Button) findViewById(R.id.btStartRx);
        this.btStopRx = (Button) findViewById(R.id.btStopRx);
        this.btClearRx = (Button) findViewById(R.id.btclearRx);
        this.btStartRx.setEnabled(true);
        this.btClearRx.setEnabled(true);
        this.btStopRx.setEnabled(false);
        this.received = (EditText) findViewById(R.id.received_edittext);
        this.error = (EditText) findViewById(R.id.error_edittext);
        this.per = (EditText) findViewById(R.id.per_edittext);
        this.btStartRx.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.31
            /* JADX WARN: Code duplicated, block: B:41:0x011b  */
            /* JADX WARN: Code duplicated, block: B:45:0x0134  */
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                WlanTest wlanTest;
                Log.d("WlanTest", "  ........ in btStartRx......");
                WlanTest.this.btStartRx.setEnabled(false);
                WlanTest.this.btStopRx.setEnabled(true);
                if (WlanTest.this.dutCommand(0, "0").equals("OK")) {
                    Log.d("WlanTest", "1.Open DUT - OK");
                    WlanTest wlanTest2 = WlanTest.this;
                    if (wlanTest2.dutCommand(16, wlanTest2.posBandRx).equals("OK")) {
                        Log.d("WlanTest", "2.Set Band - OK");
                        WlanTest wlanTest3 = WlanTest.this;
                        if (wlanTest3.dutCommand(6, wlanTest3.posChannelRx).equals("OK")) {
                            Log.d("WlanTest", "3.Set Channel - OK");
                            WlanTest wlanTest4 = WlanTest.this;
                            if (wlanTest4.dutCommand(4, wlanTest4.posAntennaRx).equals("OK")) {
                                Log.d("WlanTest", "4.Set Antenna - OK");
                                WlanTest wlanTest5 = WlanTest.this;
                                if (wlanTest5.dutCommand(26, wlanTest5.posChannelencodingRx).equals("OK")) {
                                    Log.d("WlanTest", "4-1.Set Rx Channel Encoding - OK");
                                    boolean zEquals2 = "2".equals(WlanTest.this.posOfdmaRx);
                                    WlanTest wlanTest6 = WlanTest.this;
                                    if (!zEquals2) {
                                        if ("1".equals(wlanTest6.posOfdmaRx)) {
                                            WlanTest wlanTest7 = WlanTest.this;
                                            if (wlanTest7.dutCommand(27, wlanTest7.posResourceunitRx).equals("OK")) {
                                                Log.d("WlanTest", "5.Set Resource Uint Rx Index - OK");
                                                WlanTest wlanTest8 = WlanTest.this;
                                                if (wlanTest8.dutCommand(28, wlanTest8.posBssColorRx).equals("OK")) {
                                                    Log.d("WlanTest", "6.Set BSS Color - OK");
                                                    WlanTest wlanTest9 = WlanTest.this;
                                                    if (wlanTest9.dutCommand(2, wlanTest9.posRxRuRate).equals("OK")) {
                                                        Log.d("WlanTest", "7.Set RU Data Rate - OK");
                                                        wlanTest = WlanTest.this;
                                                        if (wlanTest.dutCommand(17, wlanTest.posBandwidthRx).equals("OK")) {
                                                            Log.d("WlanTest", "8.Set BandWidth - OK");
                                                            if (WlanTest.this.dutCommand(12, "0").equals("OK")) {
                                                                Log.d("WlanTest", "9.Rx Start - OK");
                                                                return;
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        } else {
                                            wlanTest = WlanTest.this;
                                            if (wlanTest.dutCommand(17, wlanTest.posBandwidthRx).equals("OK")) {
                                                Log.d("WlanTest", "8.Set BandWidth - OK");
                                                if (WlanTest.this.dutCommand(12, "0").equals("OK")) {
                                                    Log.d("WlanTest", "9.Rx Start - OK");
                                                    return;
                                                }
                                            }
                                        }
                                    } else if (wlanTest6.dutCommand(49, "1").equals("OK")) {
                                        Log.d("WlanTest", "5.Set non-OFDMA MRU - OK");
                                        WlanTest wlanTest10 = WlanTest.this;
                                        if (wlanTest10.dutCommand(27, wlanTest10.posResourceunitRx).equals("OK")) {
                                            Log.d("WlanTest", "5.Set Resource Uint - OK");
                                            wlanTest = WlanTest.this;
                                            if (wlanTest.dutCommand(17, wlanTest.posBandwidthRx).equals("OK")) {
                                                Log.d("WlanTest", "8.Set BandWidth - OK");
                                                if (WlanTest.this.dutCommand(12, "0").equals("OK")) {
                                                    Log.d("WlanTest", "9.Rx Start - OK");
                                                    return;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Log.e("WlanTest", "Rx Test failed!");
            }
        });
        this.btStopRx.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.32
            /* JADX WARN: Code duplicated, block: B:7:0x0083  */
            @Override // android.view.View.OnClickListener
            public void onClick(View view) throws Throwable {
                Log.d("WlanTest", "  ........ in btStopRx......");
                WlanTest.this.btStopRx.setEnabled(false);
                if (WlanTest.this.dutCommand(13, "0").equals("OK")) {
                    Log.d("WlanTest", "Rx Stop - OK");
                    String strDutCommand = WlanTest.this.dutCommand(15, "0");
                    WlanTest.this.received.setText(strDutCommand);
                    String strDutCommand2 = WlanTest.this.dutCommand(14, "0");
                    WlanTest.this.error.setText(strDutCommand2);
                    int i5 = Integer.parseInt(strDutCommand2);
                    float fMax = (float) (((double) (i5 / Math.max(Integer.parseInt(strDutCommand) + i5, 1))) * 100.0d);
                    Log.d("WlanTest", "perError : " + fMax);
                    WlanTest.this.per.setText(Float.toString(fMax));
                    if (WlanTest.this.dutCommand(1, "0").equals("OK")) {
                        Log.d("WlanTest", "Close DUT - OK");
                    } else {
                        Log.e("WlanTest", "Rx Stop - failed");
                    }
                } else {
                    Log.e("WlanTest", "Rx Stop - failed");
                }
                WlanTest.this.btStartRx.setEnabled(true);
            }
        });
        this.btClearRx.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.33
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                Log.d("WlanTest", "  ........ in btClearTx......");
                WlanTest.this.btClearRx.setEnabled(true);
                WlanTest.this.received.setText("");
                WlanTest.this.error.setText("");
                WlanTest.this.per.setText("");
            }
        });
        this.linRxIqest = (LinearLayout) findViewById(R.id.wifi_noise_test);
        this.mScrollViewRxIqest = (ScrollView) findViewById(R.id.rxiqest_scrollview);
        this.mTextViewRxIqestStatus = (TextView) findViewById(R.id.rxiqest_status);
        this.btStartGetRxIqest_2G = (Button) findViewById(R.id.btStartRxIqest_2G);
        this.btStartGetRxIqest_5G = (Button) findViewById(R.id.btStartRxIqest_5G);
        this.btStartGetRxIqest_6E = (Button) findViewById(R.id.btStartRxIqest_6E);
        this.btStartGetRxIqest_2G.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest$$0
            /* JADX DEBUG: Don't trust debug lines info. Lines numbers was adjusted: min line is 0 */
            @Override // android.view.View.OnClickListener
            public final void onClick(View view) {
                this.f$0.lambda$onCreate$0(view);
            }
        });
        this.btStartGetRxIqest_5G.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest$$1
            /* JADX DEBUG: Don't trust debug lines info. Lines numbers was adjusted: min line is 0 */
            @Override // android.view.View.OnClickListener
            public final void onClick(View view) {
                this.f$0.lambda$onCreate$1(view);
            }
        });
        this.btStartGetRxIqest_6E.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest$$2
            /* JADX DEBUG: Don't trust debug lines info. Lines numbers was adjusted: min line is 0 */
            @Override // android.view.View.OnClickListener
            public final void onClick(View view) {
                this.f$0.lambda$onCreate$2(view);
            }
        });
        boolean zExists = new File("/system/lib/modules/sprdwl.ko").exists();
        this.sprdwlan = zExists;
        if (zExists) {
            Log.d("WlanTest", "Sprd WLAN Chip using");
        }
        boolean zExists2 = new File("/dev/wmtWifi").exists();
        this.mtkwlan = zExists2;
        if (zExists2) {
            Log.d("WlanTest", "MTK WLAN Chip using");
        }
        String wifiVerFromFile = getWifiVerFromFile();
        if (wifiVerFromFile != null && wifiVerFromFile.contains("DHD_ver")) {
            if (wifiVerFromFile.contains("DHD_ver")) {
                Log.d("WlanTest", "BRCM WLAN Chip");
                this.brcmwlan = true;
            }
        } else {
            Log.e("WlanTest", "file is null!");
        }
        String str2 = SystemProperties.get("ro.product.product.name");
        String wifiVerFromFile2 = getWifiVerFromFile();
        if (!TextUtils.isEmpty(wifiVerFromFile2)) {
            Log.d("WlanTest", "Version : " + wifiVerFromFile2);
            if (wifiVerFromFile2.contains("QCA6391")) {
                Log.d("WlanTest", "QCA6391 WLAN Chip");
                this.qca6391wlan = true;
            } else if (wifiVerFromFile2.contains("WCN6850")) {
                Log.d("WlanTest", "WCN6850 WLAN Chip");
                this.wcn6850wlan = true;
            } else if (wifiVerFromFile2.contains("QCOM")) {
                Log.d("WlanTest", "WCN78XX WLAN Chip");
                this.wcn78xxwlan = true;
            } else if (wifiVerFromFile2.contains("WCN6750")) {
                Log.d("WlanTest", "WCN6750 WLAN Chip");
                this.wcn6750wlan = true;
            } else if (wifiVerFromFile2.contains("WCN39XX")) {
                Log.d("WlanTest", "WCN39XX WLAN Chip");
                this.wcn39xxwlan = true;
            }
            if (str2.contains("b5q") || str2.contains("q5q") || str2.contains("e5q") || str2.contains("v5q")) {
                Log.d("WlanTest", "Need TxWaitTime");
                this.needTxWaitTime = true;
            }
        } else {
            Log.e("WlanTest", "file is null!");
        }
        String str3 = SystemProperties.get("vendor.wlbtd.version");
        if (!TextUtils.isEmpty(str3)) {
            Log.i("WlanTest", "wlbtdVer: " + str3 + ". So, used LSI BT CABLELESS Factory Mode.");
            this.lsibtcableless = true;
            String wifiVerFromFile3 = getWifiVerFromFile();
            Log.i("WlanTest", "wifiVerString: " + wifiVerFromFile3);
            if (TextUtils.isEmpty(wifiVerFromFile3) || TextUtils.equals(wifiVerFromFile3, "null")) {
                String str4 = SystemProperties.get("vendor.wlan.firmware.version");
                if (!TextUtils.isEmpty(str4)) {
                    Log.i("WlanTest", "vendor.wlan.firmware.version : " + str4);
                    wifiVerFromFile3 = str4;
                }
            }
            if (!TextUtils.isEmpty(wifiVerFromFile3) && (wifiVerFromFile3.contains("E9630") || wifiVerFromFile3.contains("E9611") || wifiVerFromFile3.contains("E9610"))) {
                Log.i("WlanTest", "Neus,Nacho,Leman and Older Chipset are not used original BT CABLELESS(Chipset limitation). Therefore, Tx Start -> Rx Start automatic operation mode.");
                this.lsibtcableless = false;
            }
        }
        checkAndDisableBleScan();
        String str5 = SystemProperties.get("sys.factory.facm_mode", "none");
        this.testType = str5;
        if ((this.brcmwlan || this.wcn78xxwlan || this.wcn6850wlan) && !this.needTxWaitTime && "bt".equals(str5) && (bluetoothAdapter = this.mBluetoothAdapter) != null && bluetoothAdapter.isEnabled()) {
            Log.d("WlanTest", "Command through Bluetooth");
            if (this.mBluetoothAdapter.isEnabled()) {
                Log.i("WlanTest", "Disable BT page scan");
                this.mBluetoothAdapter.setScanMode(20);
                try {
                    Thread.sleep(50L);
                } catch (InterruptedException unused4) {
                }
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onCreate$0(View view) {
        Log.d("WlanTest", "  ........ in btStartGetRxIqest_2G......");
        this.mTextViewRxIqestStatus.setText("");
        new Thread(new Runnable() { // from class: com.sec.android.app.wlantest.WlanTest.34
            @Override // java.lang.Runnable
            public void run() throws Throwable {
                Message message = new Message();
                message.what = 257;
                message.obj = "Start 10 sec later ...\n";
                WlanTest.this.myRxIqestGUIUpdateHandler.sendMessage(message);
                try {
                    Thread.sleep(10000L);
                } catch (InterruptedException unused) {
                }
                if (WlanTest.this.dutCommand(0, "0").equals("OK")) {
                    Log.d("WlanTest", "Open DUT - OK");
                    Log.d("WlanTest", "Get RX IQEST 2G - Start");
                    StringBuilder sb = new StringBuilder();
                    sb.append("0_");
                    for (int i = 1; i < 14; i++) {
                        sb.append(i);
                        sb.append(":");
                    }
                    sb.deleteCharAt(sb.length() - 1);
                    sb.append("_" + WlanTest.this.scanCount + "_" + WlanTest.this.maxReq);
                    String strDutCommand = WlanTest.this.dutCommand(45, sb.toString());
                    Message message2 = new Message();
                    message2.what = 257;
                    message2.obj = strDutCommand + "\n";
                    WlanTest.this.myRxIqestGUIUpdateHandler.sendMessage(message2);
                    Log.d("WlanTest", "Get RX IQEST 2G - Done, scanCount=" + WlanTest.this.scanCount + ", maxReq = " + WlanTest.this.maxReq);
                    if (WlanTest.this.dutCommand(1, "0").equals("OK")) {
                        Log.d("WlanTest", "Close DUT - OK");
                    }
                }
            }
        }).start();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onCreate$1(View view) {
        Log.d("WlanTest", "  ........ in btStartGetRxIqest_5G......");
        this.mTextViewRxIqestStatus.setText("");
        new Thread(new Runnable() { // from class: com.sec.android.app.wlantest.WlanTest.35
            @Override // java.lang.Runnable
            public void run() throws Throwable {
                Message message = new Message();
                message.what = 257;
                message.obj = "Start 10 sec later ...\n";
                WlanTest.this.myRxIqestGUIUpdateHandler.sendMessage(message);
                try {
                    Thread.sleep(10000L);
                } catch (InterruptedException unused) {
                }
                if (WlanTest.this.dutCommand(0, "0").equals("OK")) {
                    Log.d("WlanTest", "Open DUT - OK");
                    Log.d("WlanTest", "Get RX IQEST 5G - Start");
                    StringBuilder sb = new StringBuilder();
                    sb.append("1_");
                    for (int i = 36; i < 68; i += 4) {
                        sb.append(i);
                        sb.append(":");
                    }
                    for (int i2 = 100; i2 < 148; i2 += 4) {
                        sb.append(i2);
                        sb.append(":");
                    }
                    for (int i3 = 149; i3 < 181; i3 += 4) {
                        sb.append(i3);
                        sb.append(":");
                    }
                    sb.deleteCharAt(sb.length() - 1);
                    sb.append("_" + WlanTest.this.scanCount + "_" + WlanTest.this.maxReq);
                    String strDutCommand = WlanTest.this.dutCommand(45, sb.toString());
                    Message message2 = new Message();
                    message2.what = 257;
                    message2.obj = strDutCommand + "\n";
                    WlanTest.this.myRxIqestGUIUpdateHandler.sendMessage(message2);
                    Log.d("WlanTest", "Get RX IQEST 5G - Done, scanCount=" + WlanTest.this.scanCount + ", maxReq = " + WlanTest.this.maxReq);
                    if (WlanTest.this.dutCommand(1, "0").equals("OK")) {
                        Log.d("WlanTest", "Close DUT - OK");
                    }
                }
            }
        }).start();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onCreate$2(View view) {
        Log.d("WlanTest", "  ........ in btStartGetRxIqest_6E......");
        this.mTextViewRxIqestStatus.setText("");
        new Thread(new Runnable() { // from class: com.sec.android.app.wlantest.WlanTest.36
            @Override // java.lang.Runnable
            public void run() throws Throwable {
                Message message = new Message();
                message.what = 257;
                message.obj = "Start 10 sec later ...\n";
                WlanTest.this.myRxIqestGUIUpdateHandler.sendMessage(message);
                try {
                    Thread.sleep(10000L);
                } catch (InterruptedException unused) {
                }
                if (WlanTest.this.dutCommand(0, "0").equals("OK")) {
                    Log.d("WlanTest", "Open DUT - OK");
                    Log.d("WlanTest", "Get RX IQEST 6E - Start");
                    StringBuilder sb = new StringBuilder();
                    sb.append("2_");
                    for (int i = 1; i < 237; i += 4) {
                        sb.append(i);
                        sb.append(":");
                    }
                    sb.deleteCharAt(sb.length() - 1);
                    sb.append("_" + WlanTest.this.scanCount + "_" + WlanTest.this.maxReq);
                    String strDutCommand = WlanTest.this.dutCommand(45, sb.toString());
                    Message message2 = new Message();
                    message2.what = 257;
                    message2.obj = strDutCommand + "\n";
                    WlanTest.this.myRxIqestGUIUpdateHandler.sendMessage(message2);
                    Log.d("WlanTest", "Get RX IQEST 6E - Done, scanCount=" + WlanTest.this.scanCount + ", maxReq = " + WlanTest.this.maxReq);
                    if (WlanTest.this.dutCommand(1, "0").equals("OK")) {
                        Log.d("WlanTest", "Close DUT - OK");
                    }
                }
            }
        }).start();
    }

    private void checkAndDisableBleScan() {
        boolean nearbyScanning = BleUtils.getNearbyScanning(this);
        this.mRecoveryBleScanMode = nearbyScanning;
        if (nearbyScanning) {
            BleUtils.setNearbyScanning(this, false);
        }
        boolean autoHotspotSetting = BleUtils.getAutoHotspotSetting(this);
        this.mRecoveryAutoHotspotMode = autoHotspotSetting;
        if (autoHotspotSetting) {
            BleUtils.setAutoHotspot(this, false);
        }
    }

    private void recoveryBleScan() {
        if (this.mRecoveryBleScanMode) {
            BleUtils.setNearbyScanning(this, true);
        }
        if (this.mRecoveryAutoHotspotMode) {
            BleUtils.setAutoHotspot(this, true);
        }
    }

    @Override // android.app.Activity
    public boolean onCreateOptionsMenu(Menu menu) {
        super.onCreateOptionsMenu(menu);
        menu.add(0, 0, 0, "Tx Test");
        menu.add(0, 1, 1, "Center Frequency Test");
        menu.add(0, 2, 2, "Rx Test");
        menu.add(0, 3, 3, "Status");
        menu.add(0, 4, 4, "AT Commands Test");
        menu.add(0, 5, 5, "Wifi Noise Test");
        return true;
    }

    @Override // android.app.Activity
    public boolean onOptionsItemSelected(MenuItem menuItem) {
        int itemId = menuItem.getItemId();
        Log.e("WlanTest", "onOptionsItemSelected " + itemId);
        System.out.println("menu " + itemId);
        if (itemId == 0) {
            this.burst.setText("100");
            this.payload.setText("1024");
            this.absTxTest.setVisibility(0);
            this.linStatus.setVisibility(4);
            this.layoutAtCommands.setVisibility(8);
            this.absRxTest.setVisibility(4);
            this.burstTextView.setVisibility(0);
            this.payloadTextView.setVisibility(0);
            this.burst.setVisibility(0);
            this.payload.setVisibility(0);
            this.linRxIqest.setVisibility(4);
            this.mTasModeView.setVisibility(0);
        } else if (itemId == 1) {
            this.burst.setText("300");
            this.payload.setText("30");
            this.absTxTest.setVisibility(0);
            this.linStatus.setVisibility(4);
            this.layoutAtCommands.setVisibility(8);
            this.absRxTest.setVisibility(4);
            this.burstTextView.setVisibility(8);
            this.payloadTextView.setVisibility(8);
            this.burst.setVisibility(8);
            this.payload.setVisibility(8);
            this.linRxIqest.setVisibility(4);
            this.mTasModeView.setVisibility(0);
        } else if (itemId == 2) {
            this.absTxTest.setVisibility(4);
            this.linStatus.setVisibility(4);
            this.layoutAtCommands.setVisibility(8);
            this.absRxTest.setVisibility(0);
            this.linRxIqest.setVisibility(4);
            this.mTasModeView.setVisibility(4);
        } else if (itemId == 3) {
            this.absTxTest.setVisibility(4);
            this.linStatus.setVisibility(0);
            this.layoutAtCommands.setVisibility(8);
            this.absRxTest.setVisibility(4);
            this.linRxIqest.setVisibility(4);
            this.mTasModeView.setVisibility(4);
        } else if (itemId == 4) {
            this.absTxTest.setVisibility(4);
            this.linStatus.setVisibility(0);
            this.layoutAtCommands.setVisibility(0);
            this.absRxTest.setVisibility(4);
            this.linRxIqest.setVisibility(4);
            this.mTasModeView.setVisibility(4);
        } else if (itemId == 5) {
            this.linRxIqest.setVisibility(0);
            this.absTxTest.setVisibility(4);
            this.linStatus.setVisibility(4);
            this.layoutAtCommands.setVisibility(8);
            this.absRxTest.setVisibility(4);
            this.mTasModeView.setVisibility(4);
        }
        return super.onOptionsItemSelected(menuItem);
    }

    @Override // android.app.Activity
    protected void onPause() throws Throwable {
        super.onPause();
        Log.d("WlanTest", "on pause [" + this.sWakeLock + "]");
        if (this.mDriverUnloadCmdId > 0) {
            if (this.mFirmware != FWMode.NotSet) {
                Toast.makeText(this, "DO NOT RESTART WlanTest!\nPlease wait till status is shown", 1).show();
                startService("mfgloader");
                checkDriverResult("vendor.wlandriver.status", "unloaded", 5);
            }
            Intent intent = new Intent("android.intent.action.WIFI_DRIVER_INDICATION");
            intent.putExtra("STATUS", "finish");
            intent.setPackage("com.sec.facatfunction");
            sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
            Log.i("WlanTest", "onPause: Sent response intent: STATUS: finish");
            Intent intent2 = new Intent("com.sec.android.app.wlantest.WIFI_TEST_RESPONSE");
            intent2.putExtra("CMDID", this.mDriverUnloadCmdId);
            intent2.putExtra("S_DATA", this.mDriverUnloadResult);
            intent2.setPackage("com.sec.facatfunction");
            sendBroadcast(intent2, "com.sec.factory.permission.WIFI_ID_RESPONSE");
            Log.i("WlanTest", "onDestroy: Sent response intent: " + this.mDriverUnloadResult);
            this.mDriverUnloadCmdId = -1;
            this.mDriverUnloadResult = "";
            if (this.sWakeLock.isHeld()) {
                this.sWakeLock.release();
            }
            Toast.makeText(this, "Ok! You can use the WlanTest again from now on", 1).show();
            Log.d("WlanTest", "on Destroy [" + this.sWakeLock + "]");
            this.isFinishOnPause = true;
            this.mDriverHandler.getLooper().quit();
            this.mCommandHandler.getLooper().quit();
        }
        stop();
    }

    @Override // android.app.Activity
    protected void onStop() {
        super.onStop();
        enableKeyguard();
        Log.d("WlanTest", "on stop");
    }

    @Override // android.app.Activity
    protected void onDestroy() {
        BluetoothAdapter bluetoothAdapter;
        super.onDestroy();
        recoveryBleScan();
        if ((this.brcmwlan || this.wcn78xxwlan || this.wcn6850wlan) && !this.needTxWaitTime && "bt".equals(this.testType) && (bluetoothAdapter = this.mBluetoothAdapter) != null && bluetoothAdapter.isEnabled()) {
            Log.i("WlanTest", "Enable BT page scan");
            this.mBluetoothAdapter.setScanMode(21);
            try {
                Thread.sleep(50L);
            } catch (InterruptedException unused) {
            }
        }
        if (this.networkScorerStatus) {
            Settings.Global.putInt(getContentResolver(), "sem_wifi_network_rating_scorer_enabled_labs", 1);
            this.networkScorerStatus = false;
        }
        SystemProperties.set("sys.factory.wlantest.running", "0");
        unregisterReceiver(this.mReceiver);
        if (!this.isFinishOnPause) {
            if (this.mFirmware != FWMode.NotSet) {
                Toast.makeText(this, "DO NOT RESTART WlanTest!\nPlease wait till status is shown", 1).show();
                startService("mfgloader");
                checkDriverResult("vendor.wlandriver.status", "unloaded", 5);
            }
            Intent intent = new Intent("android.intent.action.WIFI_DRIVER_INDICATION");
            intent.putExtra("STATUS", "finish");
            intent.setPackage("com.sec.facatfunction");
            sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
            Log.i("WlanTest", "onDestroy: Sent response intent: STATUS: finish");
            if (this.mDriverUnloadCmdId > 0) {
                Intent intent2 = new Intent("com.sec.android.app.wlantest.WIFI_TEST_RESPONSE");
                intent2.putExtra("CMDID", this.mDriverUnloadCmdId);
                intent2.putExtra("S_DATA", this.mDriverUnloadResult);
                intent2.setPackage("com.sec.facatfunction");
                sendBroadcast(intent2, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                Log.i("WlanTest", "onDestroy: Sent response intent: " + this.mDriverUnloadResult);
                this.mDriverUnloadCmdId = -1;
                this.mDriverUnloadResult = "";
            }
            this.mDriverHandler.getLooper().quit();
            this.mCommandHandler.getLooper().quit();
            if (this.sWakeLock.isHeld()) {
                this.sWakeLock.release();
            }
            Toast.makeText(this, "Ok! You can use the WlanTest again from now on", 1).show();
            Log.d("WlanTest", "on Destroy [" + this.sWakeLock + "]");
        }
        this.isFinishOnPause = false;
    }

    @Override // android.app.Activity
    protected void onResume() {
        super.onResume();
        if (!this.sWakeLock.isHeld()) {
            this.sWakeLock.acquire();
        }
        Log.d("WlanTest", "on resume [" + this.sWakeLock + "]");
        disableKeyguard();
    }

    private synchronized void enableKeyguard() {
        setShowWhenLocked(false);
    }

    private synchronized void disableKeyguard() {
        setShowWhenLocked(true);
    }

    /* JADX WARN: Code duplicated, block: B:65:0x01b6  */
    /* JADX WARN: Code duplicated, block: B:67:0x01bb  */
    public String dutCommand(int i, String str) throws Throwable {
        Parcel parcel;
        String strConcat;
        String strConcat2;
        String allSettings;
        Parcel parcel2;
        Log.i("WlanTest", "Enter dutCommand!!! cmdId: " + i + ", data=" + str);
        if (i == 20 || i == 21 || i == 22) {
            String str2 = "\nTrying to Join [" + str + "]";
            if (this.mIsScreenOn) {
                Message message = new Message();
                message.what = 257;
                message.obj = str2;
                this.myGUIUpdateHandler.sendMessage(message);
            } else {
                this.mBufferedResultMessage += str2;
            }
        }
        if (i == 24) {
            this.mIsScreenOn = false;
            allSettings = setAllSettings(str);
            if ("OK".equals(allSettings)) {
                this.mBufferedResultMessage = "\nALL Command completed\n";
            } else {
                this.mBufferedResultMessage = "\nALL Command failed on " + allSettings + "\n";
            }
            this.mIsScreenOn = true;
        } else {
            Parcel parcelObtain = null;
            try {
                if (this.mWLService != null) {
                    Parcel parcelObtain2 = Parcel.obtain();
                    try {
                        parcelObtain = Parcel.obtain();
                        parcelObtain2.writeInterfaceToken("android.wifi.IWlanDutService");
                        parcelObtain2.writeInt(i);
                        parcelObtain2.writeString(str);
                        this.mWLService.transact(1, parcelObtain2, parcelObtain, 0);
                        String string = parcelObtain.readString();
                        parcel2 = parcelObtain;
                        parcelObtain = parcelObtain2;
                        strConcat = string;
                    } catch (RemoteException unused) {
                        parcel = parcelObtain;
                        parcelObtain = parcelObtain2;
                        try {
                            Log.e("WlanTest", "Fail to operate WLService");
                            if (parcelObtain != null) {
                                parcelObtain.recycle();
                            }
                            if (parcel != null) {
                                parcel.recycle();
                            }
                            strConcat = "NG";
                        } catch (Throwable th) {
                            th = th;
                            if (parcelObtain != null) {
                                parcelObtain.recycle();
                            }
                            if (parcel != null) {
                                parcel.recycle();
                            }
                            throw th;
                        }
                    } catch (Throwable th2) {
                        th = th2;
                        parcel = parcelObtain;
                        parcelObtain = parcelObtain2;
                        if (parcelObtain != null) {
                            parcelObtain.recycle();
                        }
                        if (parcel != null) {
                            parcel.recycle();
                        }
                        throw th;
                    }
                } else {
                    Log.e("WlanTest", "Can not get WLService");
                    strConcat = "NG";
                    parcel2 = null;
                }
                if (parcelObtain != null) {
                    parcelObtain.recycle();
                }
                if (parcel2 != null) {
                    parcel2.recycle();
                }
            } catch (RemoteException unused2) {
                parcel = null;
            } catch (Throwable th3) {
                th = th3;
                parcel = null;
            }
            Log.i("WlanTest", "After Execute DUT Command!!! result : " + strConcat);
            String str3 = "\n" + DutId.getCommandName(i);
            if (!strConcat.equals("NG")) {
                if (i == 15 || i == 14) {
                    str3 = str3 + " frame count : " + strConcat + "\n";
                    strConcat = "000000".substring(0, 6 - strConcat.length()).concat(strConcat);
                    Log.e("WlanTest", "frame count : ".concat(strConcat));
                }
                if (i == 20 || i == 21 || i == 22) {
                    strConcat2 = str3 + " - join to [" + str + "] successfully\n";
                } else {
                    strConcat2 = str3.concat(" Command completed\n");
                }
            } else if (i == 20 || i == 21 || i == 22) {
                strConcat2 = str3 + " - Fail to join [" + str + "]\n\n";
            } else {
                strConcat2 = str3.concat(" Command failed\n");
            }
            this.mBufferedResultMessage += strConcat2;
            allSettings = strConcat;
        }
        refreshTextview();
        return allSettings;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void refreshTextview() {
        if (this.mIsScreenOn) {
            Message message = new Message();
            message.what = 257;
            message.obj = this.mBufferedResultMessage;
            this.myGUIUpdateHandler.sendMessage(message);
            this.mBufferedResultMessage = "";
        }
    }

    /* JADX WARN: Code duplicated, block: B:14:0x004b A[PHI: r6
  0x004b: PHI (r6v3 int) = (r6v0 int), (r6v1 int), (r6v2 int) binds: [B:13:0x0049, B:22:0x008a, B:31:0x00c6] A[DONT_GENERATE, DONT_INLINE]] */
    /* JADX WARN: Code duplicated, block: B:8:0x0024 A[PHI: r4
  0x0024: PHI (r4v5 int) = (r4v0 int), (r4v2 int), (r4v3 int), (r4v4 int) binds: [B:7:0x0022, B:10:0x0035, B:25:0x009e, B:28:0x00b1] A[DONT_GENERATE, DONT_INLINE]] */
    private String setAllSettings(String str) {
        String[] strArrSplit = str.split(",");
        int i = 9;
        if (strArrSplit.length != 9) {
            Log.e("WlanTest", "Set AllSettings failed - The number of parameter was invalid!");
            return "NG";
        }
        int i2 = 0;
        String str2 = "OK";
        if (dutCommand(0, "0").equals("OK")) {
            i2 = 1;
            if (dutCommand(16, strArrSplit[0]).equals("OK")) {
                Log.d("WlanTest", "2.Set Band - OK");
                i2 = 6;
                int i3 = 2;
                if (dutCommand(6, strArrSplit[1]).equals("OK")) {
                    Log.d("WlanTest", "3.Set Channel - OK");
                    if (dutCommand(4, strArrSplit[2]).equals("OK")) {
                        Log.d("WlanTest", "4.Set Antenna - OK");
                        if (dutCommand(2, strArrSplit[3]).equals("OK")) {
                            Log.d("WlanTest", "5.Set Data Rate - OK");
                            i3 = 5;
                            if (dutCommand(5, strArrSplit[4]).equals("OK")) {
                                Log.d("WlanTest", "6.Set Preamble or Short Guard Interval - OK");
                                i3 = 8;
                                if (dutCommand(8, strArrSplit[5]).equals("OK")) {
                                    Log.d("WlanTest", "7.Set Burst Interval - OK");
                                    i2 = 7;
                                    if (dutCommand(9, strArrSplit[6]).equals("OK")) {
                                        Log.d("WlanTest", "8.Set PayLoad - OK");
                                        if (dutCommand(17, strArrSplit[7]).equals("OK")) {
                                            Log.d("WlanTest", "9.Set BandWidth - OK");
                                            if (dutCommand(7, strArrSplit[8]).equals("OK")) {
                                                Log.d("WlanTest", "10.Set Tx Gain - OK");
                                            } else {
                                                str2 = "NG";
                                            }
                                        } else {
                                            str2 = "NG";
                                            i = i3;
                                        }
                                    } else {
                                        str2 = "NG";
                                        i = i2;
                                    }
                                } else {
                                    str2 = "NG";
                                    i = i2;
                                }
                            } else {
                                str2 = "NG";
                                i = i3;
                            }
                        } else {
                            str2 = "NG";
                            i = 4;
                        }
                    } else {
                        str2 = "NG";
                        i = 3;
                    }
                } else {
                    str2 = "NG";
                    i = i3;
                }
            } else {
                str2 = "NG";
                i = i2;
            }
        } else {
            str2 = "NG";
            i = i2;
        }
        if (!"NG".equals(str2)) {
            return str2;
        }
        String str3 = "NG_" + i;
        Log.e("WlanTest", "Set AllSettings failed - NG on " + i);
        return str3;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public String checkDriverResult(String str, String str2, int i) {
        String vendorProperty;
        int i2 = i * 10;
        while (true) {
            int i3 = i2 - 1;
            if (i2 <= 0) {
                return "NG";
            }
            if (str.startsWith("vendor")) {
                vendorProperty = getVendorProperty(str);
            } else {
                vendorProperty = SystemProperties.get(str);
            }
            Log.d("WlanTest", str + " : " + vendorProperty);
            if (vendorProperty.equals(str2)) {
                return "OK";
            }
            if (vendorProperty.equals("failed") || vendorProperty.equals("timeout") || i3 == 0) {
                return "NG";
            }
            try {
                Thread.sleep(500L);
            } catch (InterruptedException unused) {
            }
            i2 = i3;
        }
    }

    private class CommandHandler extends Handler {
        private CommandArgs mCurrentCmd;

        public CommandHandler(Looper looper) {
            super(looper);
            this.mCurrentCmd = new CommandArgs();
        }

        /* JADX WARN: Code duplicated, block: B:154:0x04a4  */
        /* JADX WARN: Code duplicated, block: B:156:0x04ae  */
        /* JADX WARN: Code duplicated, block: B:160:0x04be  */
        /* JADX WARN: Code duplicated, block: B:164:0x04d0  */
        /* JADX WARN: Code duplicated, block: B:180:0x0551 A[PHI: r21
  0x0551: PHI (r21v1 java.lang.String) = 
  (r21v0 java.lang.String)
  (r21v0 java.lang.String)
  (r21v0 java.lang.String)
  (r21v0 java.lang.String)
  (r21v0 java.lang.String)
  (r21v0 java.lang.String)
  (r21v3 java.lang.String)
  (r21v3 java.lang.String)
  (r21v3 java.lang.String)
 binds: [B:161:0x04c8, B:163:0x04ce, B:165:0x04d4, B:167:0x04e0, B:175:0x051f, B:159:0x04bc, B:125:0x03ce, B:127:0x03d6, B:131:0x03e6] A[DONT_GENERATE, DONT_INLINE]] */
        /* JADX WARN: Code duplicated, block: B:183:0x0561  */
        /* JADX WARN: Code duplicated, block: B:185:0x0567  */
        /* JADX WARN: Code duplicated, block: B:186:0x0570  */
        /* JADX WARN: Code duplicated, block: B:187:0x0572  */
        /* JADX WARN: Code duplicated, block: B:196:0x0590  */
        /* JADX WARN: Code duplicated, block: B:285:0x07cc  */
        /* JADX WARN: Code duplicated, block: B:313:0x088a  */
        /* JADX WARN: Code duplicated, block: B:315:0x088e  */
        @Override // android.os.Handler
        public void handleMessage(Message message) throws Throwable {
            String str;
            WlanTest wlanTest;
            String strDutCommand;
            int i;
            int i2;
            int i3;
            String str2;
            String strDutCommand2;
            int i4;
            int i5;
            Intent intent = new Intent();
            intent.setPackage("com.sec.facatfunction");
            int i6 = message.what;
            if (i6 == 261) {
                if (this.mCurrentCmd.cmdId == 100) {
                    return;
                }
                intent.setAction("com.sec.android.app.wlantest.WIFI_TEST_RESPONSE");
                intent.putExtra("CMDID", this.mCurrentCmd.cmdId);
                String strDutCommand3 = (String) message.obj;
                if (strDutCommand3.equals("OK") && this.mCurrentCmd.cmdId == 0) {
                    strDutCommand3 = WlanTest.this.dutCommand(0, "0");
                }
                if (WlanTest.this.sprdwlan && strDutCommand3.equals("OK") && this.mCurrentCmd.cmdId == 18) {
                    strDutCommand3 = WlanTest.this.dutCommand(0, "0");
                }
                if (WlanTest.this.mtkwlan && strDutCommand3.equals("OK") && this.mCurrentCmd.cmdId == 18) {
                    strDutCommand3 = WlanTest.this.dutCommand(18, "0");
                }
                intent.putExtra("S_DATA", strDutCommand3);
                CommandArgs commandArgs = this.mCurrentCmd;
                int i7 = commandArgs.cmdId;
                if (i7 == 1 || i7 == 19) {
                    WlanTest.this.mDriverUnloadCmdId = i7;
                    WlanTest.this.mDriverUnloadResult = strDutCommand3;
                    this.mCurrentCmd.cmdId = 100;
                    WlanTest.this.finish();
                    return;
                }
                commandArgs.cmdId = 100;
                WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                Log.i("WlanTest", "Sent response intent: " + strDutCommand3);
                return;
            }
            if (i6 == 262) {
                if (!WlanTest.this.sWakeLock.isHeld()) {
                    WlanTest.this.sWakeLock.acquire();
                    Log.e("WlanTest", "onReceive [" + WlanTest.this.sWakeLock + "]");
                }
                intent.setAction("com.sec.android.app.wlantest.WIFI_TEST_RESPONSE");
                intent.putExtra("CMDID", this.mCurrentCmd.cmdId);
                CommandArgs commandArgs2 = (CommandArgs) message.obj;
                Log.d("WlanTest", "mCurrentCmd.cmdId : " + this.mCurrentCmd.cmdId + "(" + DutId.getCommandName(this.mCurrentCmd.cmdId) + "), args.cmdId : " + commandArgs2.cmdId + "(" + DutId.getCommandName(commandArgs2.cmdId) + ")");
                StringBuilder sb = new StringBuilder("mFirmware : <");
                sb.append(WlanTest.this.mFirmware);
                sb.append(">");
                Log.d("WlanTest", sb.toString());
                int i8 = commandArgs2.cmdId;
                if ((i8 == 1 || i8 == 19) && WlanTest.this.mFirmware == FWMode.NotSet) {
                    intent.putExtra("S_DATA", "OK");
                    WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                    Log.i("WlanTest", "Sent response intent: OK");
                    WlanTest.this.sWakeLock.release();
                    Log.d("WlanTest", "release wakelock by " + commandArgs2.cmdId + " [" + WlanTest.this.sWakeLock + "]");
                    return;
                }
                int i9 = this.mCurrentCmd.cmdId;
                int i10 = commandArgs2.cmdId;
                if (i9 == i10) {
                    Log.i("WlanTest", "Skip Command : Command ID <" + commandArgs2.cmdId + "> is already running");
                    WlanTest.this.appendBufferedResult("NG", "INVALID (already running)");
                    WlanTest.this.refreshTextview();
                    return;
                }
                if (i9 == 100 && i10 != 100) {
                    FWMode fWMode = WlanTest.this.mFirmware;
                    FWMode fWMode2 = FWMode.NotSet;
                    if (fWMode != fWMode2 || (i5 = commandArgs2.cmdId) == 0 || i5 == 18 || i5 == 46) {
                        this.mCurrentCmd = commandArgs2;
                        int i11 = commandArgs2.cmdId;
                        if (i11 == 0) {
                            if (WlanTest.this.mFirmware == fWMode2) {
                                Message message2 = new Message();
                                message2.what = 258;
                                message2.obj = "test";
                                WlanTest.this.setVendorProperty("vendor.wlandriver.mode", "test");
                                WlanTest.this.mDriverHandler.sendMessage(message2);
                                return;
                            }
                            if (WlanTest.this.mFirmware == FWMode.NormalMode) {
                                Message message3 = new Message();
                                message3.what = 260;
                                message3.obj = "test";
                                WlanTest.this.setVendorProperty("vendor.wlandriver.mode", "test");
                                WlanTest.this.mDriverHandler.sendMessage(message3);
                                return;
                            }
                        } else if (i11 == 18) {
                            if (WlanTest.this.mFirmware == fWMode2) {
                                Message message4 = new Message();
                                message4.what = 258;
                                message4.obj = "normal";
                                WlanTest.this.setVendorProperty("vendor.wlandriver.mode", "normal");
                                WlanTest.this.mDriverHandler.sendMessage(message4);
                                return;
                            }
                            if (WlanTest.this.mFirmware == FWMode.TestMode) {
                                Message message5 = new Message();
                                message5.what = 260;
                                message5.obj = "normal";
                                WlanTest.this.setVendorProperty("vendor.wlandriver.mode", "normal");
                                WlanTest.this.mDriverHandler.sendMessage(message5);
                                return;
                            }
                        } else if (i11 == 16) {
                            boolean zEquals = "1".equals(commandArgs2.data);
                            WlanTest wlanTest2 = WlanTest.this;
                            if (zEquals) {
                                wlanTest2.is24G = true;
                            } else {
                                wlanTest2.is24G = false;
                            }
                        } else {
                            if (i11 == 2) {
                                if (WlanTest.this.is24G) {
                                    String str3 = commandArgs2.data;
                                    Log.d("WlanTest", "Set Data Rate " + str3);
                                    if ("06".equals(str3) || "6".equals(str3)) {
                                        boolean z = WlanTest.this.brcmwlan;
                                        WlanTest wlanTest3 = WlanTest.this;
                                        if (z) {
                                            wlanTest3.txWaitTime = 4000L;
                                        } else {
                                            wlanTest3.txWaitTime = 4000L;
                                            WlanTest.this.rxWaitTime = 3000L;
                                        }
                                    } else if ("22".equals(str3)) {
                                        boolean z2 = WlanTest.this.brcmwlan;
                                        WlanTest wlanTest4 = WlanTest.this;
                                        if (z2) {
                                            wlanTest4.txWaitTime = 3000L;
                                        } else {
                                            wlanTest4.txWaitTime = 4000L;
                                            WlanTest.this.rxWaitTime = 1000L;
                                        }
                                    }
                                } else {
                                    Log.d("WlanTest", "DUT is set 5G. Do not change Wait Time");
                                }
                            }
                            if (((WlanTest.this.wcn39xxwlan && !WlanTest.this.wcn6750wlan && !WlanTest.this.brcmwlan && !WlanTest.this.wcn78xxwlan && !WlanTest.this.wcn6850wlan && !WlanTest.this.mtkwlan) || WlanTest.this.needTxWaitTime) && "bt".equals(WlanTest.this.testType)) {
                                WlanTest wlanTest5 = WlanTest.this;
                                if (wlanTest5.is24G && wlanTest5.mBluetoothAdapter != null && WlanTest.this.mBluetoothAdapter.isEnabled()) {
                                    Log.d("WlanTest", "Command through Bluetooth");
                                    int i12 = commandArgs2.cmdId;
                                    if (i12 == 10) {
                                        if (WlanTest.this.lsibtcableless) {
                                            WlanTest.this.txWaitTime = Long.parseLong(commandArgs2.data) > 0 ? Long.parseLong(commandArgs2.data) : 4000L;
                                        }
                                        StringBuilder sb2 = new StringBuilder("Tx Wait Time is ");
                                        str = "INVALID (already running)";
                                        sb2.append(WlanTest.this.txWaitTime);
                                        Log.d("WlanTest", sb2.toString());
                                        WlanTest.this.isTxTestPassed = true;
                                        intent.putExtra("S_DATA", WlanTest.this.dutCommand(commandArgs2.cmdId, commandArgs2.data));
                                        WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                        if (WlanTest.this.mBluetoothAdapter.isEnabled() && !WlanTest.this.lsibtcableless) {
                                            Log.e("WlanTest", "Tx Start command is received. BT Page Scan off");
                                            WlanTest.this.mBluetoothAdapter.setScanMode(20);
                                        }
                                        try {
                                            Thread.sleep(WlanTest.this.txWaitTime);
                                        } catch (InterruptedException unused) {
                                        }
                                        Log.e("WlanTest", "Tx Test Timer is finished.");
                                        strDutCommand = WlanTest.this.dutCommand(11, "0");
                                        intent.putExtra("S_DATA", strDutCommand);
                                        WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                        if (!WlanTest.this.lsibtcableless) {
                                            strDutCommand = WlanTest.this.dutCommand(12, "0");
                                            intent.putExtra("S_DATA", strDutCommand);
                                            WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                            try {
                                                Thread.sleep(1000L);
                                            } catch (InterruptedException unused2) {
                                            }
                                            if (WlanTest.this.mBluetoothAdapter.isEnabled()) {
                                                Log.e("WlanTest", "Rx Test is finished. BT Page Scan on");
                                                WlanTest.this.mBluetoothAdapter.setScanMode(21);
                                            }
                                        }
                                        WlanTest.this.isBtTest = true;
                                    } else {
                                        str = "INVALID (already running)";
                                        if (i12 == 12 && !WlanTest.this.isTxTestPassed && (WlanTest.this.qca6391wlan || WlanTest.this.lsibtcableless)) {
                                            if (WlanTest.this.lsibtcableless) {
                                                WlanTest.this.rxWaitTime = Long.parseLong(commandArgs2.data) > 0 ? Long.parseLong(commandArgs2.data) : 1000L;
                                            }
                                            Log.d("WlanTest", "Rx Wait Time is " + WlanTest.this.rxWaitTime);
                                            strDutCommand = WlanTest.this.dutCommand(commandArgs2.cmdId, commandArgs2.data);
                                            intent.putExtra("S_DATA", strDutCommand);
                                            WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                            if (WlanTest.this.mBluetoothAdapter.isEnabled() && !WlanTest.this.lsibtcableless) {
                                                Log.e("WlanTest", "Rx Start command is received. BT Page Scan off");
                                                WlanTest.this.mBluetoothAdapter.setScanMode(20);
                                            }
                                            try {
                                                Thread.sleep(WlanTest.this.rxWaitTime);
                                            } catch (InterruptedException unused3) {
                                            }
                                            Log.e("WlanTest", "Rx Test Timer is finished.");
                                            if (WlanTest.this.mBluetoothAdapter.isEnabled() && !WlanTest.this.lsibtcableless) {
                                                Log.e("WlanTest", "Rx Test is finished. BT Page Scan on");
                                                WlanTest.this.mBluetoothAdapter.setScanMode(21);
                                            }
                                            if (WlanTest.this.lsibtcableless) {
                                                strDutCommand = WlanTest.this.dutCommand(13, "0");
                                                intent.putExtra("S_DATA", strDutCommand);
                                                WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                            }
                                            WlanTest.this.isBtTest = true;
                                        } else {
                                            strDutCommand = "";
                                        }
                                    }
                                } else {
                                    str = "INVALID (already running)";
                                    if (WlanTest.this.wcn39xxwlan) {
                                        wlanTest = WlanTest.this;
                                        if (!wlanTest.is24G) {
                                            strDutCommand = "";
                                        } else {
                                            strDutCommand = "";
                                        }
                                    } else {
                                        wlanTest = WlanTest.this;
                                        if (!wlanTest.is24G) {
                                            strDutCommand = "";
                                        } else {
                                            strDutCommand = "";
                                        }
                                    }
                                }
                            } else {
                                str = "INVALID (already running)";
                                if ((WlanTest.this.wcn39xxwlan || WlanTest.this.wcn6850wlan || WlanTest.this.wcn78xxwlan) && "bt".equals(WlanTest.this.testType)) {
                                    wlanTest = WlanTest.this;
                                    if (!wlanTest.is24G && wlanTest.mBluetoothAdapter != null && WlanTest.this.mBluetoothAdapter.isEnabled()) {
                                        Log.d("WlanTest", "Command through Bluetooth");
                                        int i13 = commandArgs2.cmdId;
                                        if (i13 == 10) {
                                            strDutCommand = WlanTest.this.dutCommand(i13, commandArgs2.data);
                                            intent.putExtra("S_DATA", strDutCommand);
                                            WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                            if (WlanTest.this.mBluetoothAdapter.isEnabled()) {
                                                Log.e("WlanTest", "QC WLAN - Tx Start command is received. BT Page Scan off");
                                                WlanTest.this.mBluetoothAdapter.setScanMode(20);
                                            }
                                            WlanTest.this.isBtTest = true;
                                        } else if (i13 == 11) {
                                            strDutCommand = WlanTest.this.dutCommand(11, "0");
                                            intent.putExtra("S_DATA", strDutCommand);
                                            WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                            if (WlanTest.this.mBluetoothAdapter.isEnabled()) {
                                                Log.e("WlanTest", "QC WLAN - Tx Stop command is received. BT Page Scan on");
                                                WlanTest.this.mBluetoothAdapter.setScanMode(21);
                                            }
                                            WlanTest.this.isBtTest = true;
                                        } else {
                                            strDutCommand = "";
                                        }
                                    } else {
                                        strDutCommand = "";
                                    }
                                } else {
                                    strDutCommand = "";
                                }
                            }
                            WlanTest.this.isTxTestPassed = false;
                            if (WlanTest.this.sprdwlan) {
                                i2 = 19;
                                if (commandArgs2.cmdId == 19) {
                                    Log.i("WlanTest", "SPRD Shuld use CD instead of NU");
                                    i = 1;
                                    commandArgs2.cmdId = 1;
                                } else {
                                    i = 1;
                                }
                            } else {
                                i = 1;
                                i2 = 19;
                            }
                            if (WlanTest.this.mtkwlan && commandArgs2.cmdId == i2) {
                                Log.i("WlanTest", "MTK Shuld use CD instead of NU");
                                commandArgs2.cmdId = i;
                            }
                            i3 = commandArgs2.cmdId;
                            if (i3 == 18 && i3 != i2) {
                                if (i3 != 41) {
                                    str2 = "OK";
                                    if (i3 == 10 || i3 == 11 || i3 == 12 || i3 == 13) {
                                        WlanTest wlanTest6 = WlanTest.this;
                                        if (wlanTest6.isBtTest && wlanTest6.is24G) {
                                            wlanTest6.isBtTest = false;
                                            Log.i("WlanTest", " dutCommand() already finished. " + commandArgs2.cmdId);
                                            this.mCurrentCmd.cmdId = 100;
                                            return;
                                        }
                                    }
                                    if (i3 == 50) {
                                        if ("bt".equals(WlanTest.this.testType) && WlanTest.this.mBluetoothAdapter != null && WlanTest.this.mBluetoothAdapter.isEnabled()) {
                                            Log.i("WlanTest", "Disable BT page scan");
                                            WlanTest.this.mBluetoothAdapter.setScanMode(20);
                                            try {
                                                Thread.sleep(50L);
                                            } catch (InterruptedException unused4) {
                                            }
                                        }
                                        String[] strArrSplit = commandArgs2.data.split("_");
                                        if (strArrSplit[1].equals("all")) {
                                            String str4 = strArrSplit[0];
                                            String str5 = strArrSplit[2];
                                            StringBuilder sb3 = new StringBuilder();
                                            if (str4.equals("0")) {
                                                for (int i14 = 1; i14 < 14; i14++) {
                                                    sb3.append(i14);
                                                    sb3.append(":");
                                                }
                                            } else if (str4.equals("1")) {
                                                for (int i15 = 36; i15 < 68; i15 += 4) {
                                                    sb3.append(i15);
                                                    sb3.append(":");
                                                }
                                                for (int i16 = 100; i16 < 148; i16 += 4) {
                                                    sb3.append(i16);
                                                    sb3.append(":");
                                                }
                                                for (int i17 = 149; i17 < 181; i17 += 4) {
                                                    sb3.append(i17);
                                                    sb3.append(":");
                                                }
                                            } else {
                                                for (int i18 = 1; i18 < 237; i18 += 4) {
                                                    sb3.append(i18);
                                                    sb3.append(":");
                                                }
                                            }
                                            sb3.deleteCharAt(sb3.length() - 1);
                                            WlanTest wlanTest7 = WlanTest.this;
                                            wlanTest7.griData = wlanTest7.dutCommand(45, str4 + "_" + ((CharSequence) sb3) + "_" + str5);
                                        } else {
                                            WlanTest wlanTest8 = WlanTest.this;
                                            wlanTest8.griData = wlanTest8.dutCommand(45, commandArgs2.data);
                                        }
                                        Log.d("WlanTest", "AT Test, Get RX IQEST - Complete");
                                        if ("bt".equals(WlanTest.this.testType) && WlanTest.this.mBluetoothAdapter != null && WlanTest.this.mBluetoothAdapter.isEnabled()) {
                                            Log.i("WlanTest", "Enable BT page scan");
                                            WlanTest.this.mBluetoothAdapter.setScanMode(21);
                                            try {
                                                Thread.sleep(50L);
                                            } catch (InterruptedException unused5) {
                                            }
                                        }
                                        this.mCurrentCmd.cmdId = 100;
                                        return;
                                    }
                                    if (i3 == 45) {
                                        CommandArgs commandArgs3 = new CommandArgs();
                                        commandArgs3.cmdId = 50;
                                        commandArgs3.data = commandArgs2.data;
                                        Message message6 = new Message();
                                        message6.what = 262;
                                        message6.obj = commandArgs3;
                                        WlanTest.this.mCommandHandler.sendMessageDelayed(message6, 1000L);
                                    } else if (i3 == 46) {
                                        Log.d("WlanTest", "args.data=" + commandArgs2.data);
                                        if ("3".equals(commandArgs2.data) || "4".equals(commandArgs2.data) || "5".equals(commandArgs2.data)) {
                                            if (WlanTest.this.DoShellCmd("/vendor/bin/enable_test_mode.sh " + commandArgs2.data) == 1) {
                                                strDutCommand2 = str2;
                                            } else {
                                                strDutCommand2 = strDutCommand;
                                            }
                                        } else {
                                            strDutCommand2 = strDutCommand;
                                        }
                                        WlanTest.this.appendBufferedResult(strDutCommand2, DutId.getCommandName(46));
                                        WlanTest.this.refreshTextview();
                                    } else if (i3 == 53) {
                                        strDutCommand2 = WlanTest.this.setDcxoCalibrationData(commandArgs2.data) ? str2 : "NG";
                                        WlanTest.this.appendBufferedResult(strDutCommand2, DutId.getCommandName(53));
                                        WlanTest.this.refreshTextview();
                                    } else if (i3 == 54) {
                                        strDutCommand2 = WlanTest.this.getDcxoCalibrationData();
                                        WlanTest.this.appendBufferedResult(strDutCommand2, DutId.getCommandName(54));
                                        WlanTest.this.refreshTextview();
                                    } else if (i3 == 58) {
                                        strDutCommand2 = WlanTest.this.dutCommand(i3, "0");
                                        WlanTest.this.appendBufferedResult(strDutCommand2, DutId.getCommandName(58));
                                    } else if (i3 == 56) {
                                        Log.d("WlanTest", "Set SSID " + commandArgs2.data);
                                        strDutCommand2 = WlanTest.this.dutCommand(commandArgs2.cmdId, commandArgs2.data);
                                        intent.putExtra("S_DATA", strDutCommand2);
                                        WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                    } else if (DutId.isValidCommand(i3) || commandArgs2.bypass) {
                                        strDutCommand2 = WlanTest.this.dutCommand(commandArgs2.cmdId, commandArgs2.data);
                                        Log.i("WlanTest", " dutCommand() Complete.");
                                    } else {
                                        WlanTest.this.appendBufferedResult("NG", str);
                                        WlanTest.this.refreshTextview();
                                        strDutCommand2 = strDutCommand;
                                    }
                                } else if (commandArgs2.data.equals("0")) {
                                    String cidInfoFromFile = WlanTest.this.getCidInfoFromFile();
                                    if (cidInfoFromFile.length() < 3) {
                                        Log.e("WlanTest", "cid_info not written correctly");
                                    } else {
                                        Log.i("WlanTest", "cid_info = ".concat(cidInfoFromFile));
                                        if ("sem".equals(cidInfoFromFile.substring(0, 3))) {
                                            strDutCommand2 = "0";
                                        }
                                    }
                                    strDutCommand2 = "1";
                                } else if (commandArgs2.data.equals("1")) {
                                    WlanTest wlanTest9 = WlanTest.this;
                                    wlanTest9.appendBufferedResult("OK", wlanTest9.griData);
                                    strDutCommand2 = WlanTest.this.griData;
                                    WlanTest.this.refreshTextview();
                                } else {
                                    strDutCommand2 = strDutCommand;
                                }
                                i4 = commandArgs2.cmdId;
                                if ((i4 != 1 || i4 == 19) && WlanTest.this.mFirmware != FWMode.NotSet) {
                                    WlanTest.this.mDriverHandler.sendEmptyMessage(259);
                                    return;
                                }
                                intent.putExtra("S_DATA", strDutCommand2);
                                WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                                Log.i("WlanTest", "Sent response intent: " + strDutCommand2);
                                this.mCurrentCmd.cmdId = 100;
                                return;
                            }
                            str2 = "OK";
                            strDutCommand2 = str2;
                            i4 = commandArgs2.cmdId;
                            if (i4 != 1) {
                                WlanTest.this.mDriverHandler.sendEmptyMessage(259);
                                return;
                            } else {
                                WlanTest.this.mDriverHandler.sendEmptyMessage(259);
                                return;
                            }
                            intent.putExtra("S_DATA", strDutCommand2);
                            WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                            Log.i("WlanTest", "Sent response intent: " + strDutCommand2);
                            this.mCurrentCmd.cmdId = 100;
                            return;
                        }
                        if (WlanTest.this.wcn39xxwlan) {
                        }
                        str = "INVALID (already running)";
                        if (WlanTest.this.wcn39xxwlan) {
                            wlanTest = WlanTest.this;
                            if (!wlanTest.is24G) {
                                strDutCommand = "";
                            } else {
                                strDutCommand = "";
                            }
                        } else {
                            wlanTest = WlanTest.this;
                            if (!wlanTest.is24G) {
                                strDutCommand = "";
                            } else {
                                strDutCommand = "";
                            }
                        }
                        WlanTest.this.isTxTestPassed = false;
                        if (WlanTest.this.sprdwlan) {
                            i2 = 19;
                            if (commandArgs2.cmdId == 19) {
                                Log.i("WlanTest", "SPRD Shuld use CD instead of NU");
                                i = 1;
                                commandArgs2.cmdId = 1;
                            } else {
                                i = 1;
                            }
                        } else {
                            i = 1;
                            i2 = 19;
                        }
                        if (WlanTest.this.mtkwlan) {
                            Log.i("WlanTest", "MTK Shuld use CD instead of NU");
                            commandArgs2.cmdId = i;
                        }
                        i3 = commandArgs2.cmdId;
                        if (i3 == 18) {
                            str2 = "OK";
                            strDutCommand2 = str2;
                        } else {
                            str2 = "OK";
                            strDutCommand2 = str2;
                        }
                        i4 = commandArgs2.cmdId;
                        if (i4 != 1) {
                            WlanTest.this.mDriverHandler.sendEmptyMessage(259);
                            return;
                        } else {
                            WlanTest.this.mDriverHandler.sendEmptyMessage(259);
                            return;
                        }
                        intent.putExtra("S_DATA", strDutCommand2);
                        WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                        Log.i("WlanTest", "Sent response intent: " + strDutCommand2);
                        this.mCurrentCmd.cmdId = 100;
                        return;
                    }
                }
                Log.e("WlanTest", "Wrong Wlan Test Command.");
                intent.putExtra("S_DATA", "NG");
                WlanTest.this.sendBroadcast(intent, "com.sec.factory.permission.WIFI_ID_RESPONSE");
                Log.i("WlanTest", "Sent response intent: NG");
                return;
            }
            super.handleMessage(message);
        }
    }

    private class DriverHandler extends Handler {
        public DriverHandler(Looper looper) {
            super(looper);
        }

        @Override // android.os.Handler
        public void handleMessage(Message message) {
            Message message2 = new Message();
            Message message3 = new Message();
            switch (message.what) {
                case 258:
                    String str = (String) message.obj;
                    if (str.contains("test") || str.equals("normal")) {
                        WlanTest.this.startService("mfgloader");
                        Log.d("WlanTest", "DriverHandler - EVENT_LOAD_DRIVER - mode : ".concat(str));
                        String strCheckDriverResult = WlanTest.this.checkDriverResult("vendor.wlandriver.status", "ok", 10);
                        message2.obj = strCheckDriverResult;
                        boolean zEquals = strCheckDriverResult.equals("OK");
                        WlanTest wlanTest = WlanTest.this;
                        if (zEquals) {
                            wlanTest.mFirmware = str.contains("test") ? FWMode.TestMode : FWMode.NormalMode;
                        } else {
                            wlanTest.startService("mfgloader");
                            try {
                                Thread.sleep(1000L);
                                break;
                            } catch (InterruptedException unused) {
                            }
                            WlanTest.this.mFirmware = FWMode.NotSet;
                        }
                    } else {
                        message2.obj = "NG";
                    }
                    message2.what = 261;
                    WlanTest.this.mCommandHandler.sendMessage(message2);
                    message3.what = 257;
                    message3.obj = "\n\n " + WlanTest.this.mFirmware + " Driver loaded [" + ((String) message2.obj) + "]\n";
                    WlanTest.this.myGUIUpdateHandler.sendMessage(message3);
                    break;
                case 259:
                    message2.what = 261;
                    WlanTest.this.startService("mfgloader");
                    String strCheckDriverResult2 = WlanTest.this.checkDriverResult("vendor.wlandriver.status", "unloaded", 10);
                    message2.obj = strCheckDriverResult2;
                    if (strCheckDriverResult2.equals("OK")) {
                        WlanTest.this.mFirmware = FWMode.NotSet;
                    }
                    WlanTest.this.mCommandHandler.sendMessage(message2);
                    message3.what = 257;
                    message3.obj = "\n\n Driver unloaded [" + ((String) message2.obj) + "]\n";
                    WlanTest.this.myGUIUpdateHandler.sendMessage(message3);
                    break;
                case 260:
                    message2.what = 261;
                    String str2 = (String) message.obj;
                    if (str2.contains("test") || str2.equals("normal")) {
                        WlanTest.this.startService("mfgloader");
                        Log.d("WlanTest", "DriverHandler - EVENT_CHANGE_DRIVER - mode : ".concat(str2));
                        String strCheckDriverResult3 = WlanTest.this.checkDriverResult("vendor.wlandriver.status", "unloaded", 5);
                        message2.obj = strCheckDriverResult3;
                        if (strCheckDriverResult3.equals("OK")) {
                            WlanTest.this.mFirmware = FWMode.NotSet;
                            WlanTest.this.startService("mfgloader");
                            String strCheckDriverResult4 = WlanTest.this.checkDriverResult("vendor.wlandriver.status", "ok", 10);
                            message2.obj = strCheckDriverResult4;
                            boolean zEquals2 = strCheckDriverResult4.equals("OK");
                            WlanTest wlanTest2 = WlanTest.this;
                            if (zEquals2) {
                                wlanTest2.mFirmware = str2.contains("test") ? FWMode.TestMode : FWMode.NormalMode;
                            } else {
                                wlanTest2.startService("mfgloader");
                                try {
                                    Thread.sleep(1000L);
                                    break;
                                } catch (InterruptedException unused2) {
                                }
                            }
                        } else {
                            message2.obj = "NG";
                        }
                    } else {
                        message2.obj = "NG";
                    }
                    WlanTest.this.mCommandHandler.sendMessage(message2);
                    message3.what = 257;
                    message3.obj = "\n\n Driver changed to " + WlanTest.this.mFirmware + " [" + ((String) message2.obj) + "]\n";
                    WlanTest.this.myGUIUpdateHandler.sendMessage(message3);
                    break;
                default:
                    super.handleMessage(message);
                    break;
            }
        }
    }

    public void stop() throws Throwable {
        if (this.mProxSensor == null || !this.mIsActive) {
            return;
        }
        Log.d("WlanTest", "Proximity sensor stopped at : " + System.currentTimeMillis());
        this.mIsActive = false;
        if (this.mIsClose) {
            Log.d("WlanTest", "going back to normal Txpower on un-reg ProxSensor");
            dutCommand(7, this.posPower);
        }
        this.mSensorManager.unregisterListener(this.mListener);
        Log.d("WlanTest", "ProxSensor unregisterListener complete");
    }

    public void start() {
        Sensor sensor = this.mProxSensor;
        if (sensor == null || this.mIsActive) {
            return;
        }
        this.mIsActive = true;
        this.mSensorManager.registerListener(this.mListener, sensor, 2);
        Log.d("WlanTest", "Proximity sensor registered at : " + System.currentTimeMillis());
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean startService(String str) {
        int i = 10;
        while (true) {
            int i2 = i - 1;
            if (i > 0) {
                if (!SystemProperties.get("init.svc." + str).equals("running")) {
                    SystemService.start(str);
                    return true;
                }
                try {
                    Thread.sleep(500L);
                } catch (InterruptedException unused) {
                }
                i = i2;
            } else {
                Log.e("WlanTest", "Can't start service because " + str + " is running");
                return false;
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Code duplicated, block: B:51:0x0146  */
    /* JADX WARN: Code duplicated, block: B:55:0x015f  */
    public void startRsdbTx(String str) {
        this.posBurstTx = this.burst.getText().toString();
        this.posPayloadTx = this.payload.getText().toString();
        if (dutCommand(0, str).equals("OK")) {
            Log.d("WlanTest", "1.Open DUT - OK");
            if (dutCommand(16, this.posBandTx).equals("OK")) {
                Log.d("WlanTest", "2.Set Band - OK");
                if (dutCommand(6, this.posChannelTx).equals("OK")) {
                    Log.d("WlanTest", "3.Set Channel - OK");
                    if (dutCommand(4, this.posAntennaTx).equals("OK")) {
                        Log.d("WlanTest", "4.Set Antenna - OK");
                        if (dutCommand(2, this.posTxRate).equals("OK")) {
                            Log.d("WlanTest", "5.Set Data Rate - OK");
                            if (dutCommand(5, this.posPreambleTx).equals("OK")) {
                                Log.d("WlanTest", "6.Set Preamble or Short Guard Interval - OK");
                                if (dutCommand(8, this.posBurstTx).equals("OK")) {
                                    Log.d("WlanTest", "7.Set Burst Interval - OK");
                                    if (dutCommand(9, this.posPayloadTx).equals("OK")) {
                                        Log.d("WlanTest", "8.Set PayLoad - OK");
                                        if (dutCommand(17, this.posBandwidthTx).equals("OK")) {
                                            Log.d("WlanTest", "9.Set BandWidth - OK");
                                            if (dutCommand(26, this.posChannelencodingTx).equals("OK")) {
                                                Log.d("WlanTest", "10.Set Channel Encoding - OK");
                                                if ("2".equals(this.posOfdmaTx)) {
                                                    if (dutCommand(49, "1").equals("OK")) {
                                                        Log.d("WlanTest", "11.Set non-OFDMA MRU - OK");
                                                        if (dutCommand(27, this.posResourceunitTx).equals("OK")) {
                                                            Log.d("WlanTest", "11.Set Resource Uint - OK");
                                                            if (dutCommand(7, this.posPower).equals("OK")) {
                                                                Log.d("WlanTest", "12.Set Tx Gain - OK");
                                                                if (dutCommand(10, this.posPacketTx).equals("OK")) {
                                                                    Log.d("WlanTest", "13.Tx Start - OK");
                                                                    return;
                                                                }
                                                            }
                                                        }
                                                    }
                                                } else {
                                                    if ("1".equals(this.posOfdmaTx)) {
                                                        if (dutCommand(27, this.posResourceunitTx).equals("OK")) {
                                                            Log.d("WlanTest", "11.Set Resource Uint - OK");
                                                        }
                                                    } else {
                                                        Log.d("WlanTest", "11.Set Resource Uint - Bandwith doesnot support RU");
                                                    }
                                                    if (dutCommand(7, this.posPower).equals("OK")) {
                                                        Log.d("WlanTest", "12.Set Tx Gain - OK");
                                                        if (dutCommand(10, this.posPacketTx).equals("OK")) {
                                                            Log.d("WlanTest", "13.Tx Start - OK");
                                                            return;
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        Log.e("WlanTest", "Tx Test failed!");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public String getCidInfoFromFile() {
        return TextUtils.equals(this.mSemWifiManager.getWifiCid(), "null") ? "" : this.mSemWifiManager.getWifiCid();
    }

    private String getWifiVerFromFile() {
        return this.mSemWifiManager.getWifiVersions();
    }

    private String getWifiSupportedFeatureSet() {
        String wifiSupportedFeatureSet = this.mSemWifiManager.getWifiSupportedFeatureSet();
        if (wifiSupportedFeatureSet == null) {
            return "Unavailable";
        }
        return wifiSupportedFeatureSet.replace("\n", "");
    }

    private String getTasMode() {
        String tasMode = this.mSemWifiManager.getTasMode();
        if (tasMode == null) {
            return "Unknown";
        }
        return tasMode.replace("\n", "");
    }

    private String getVendorProperty(String str) {
        String vendorWlanDriverProp = this.mSemWifiManager.getVendorWlanDriverProp(str);
        return vendorWlanDriverProp == null ? "" : vendorWlanDriverProp;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean setVendorProperty(String str, String str2) {
        return this.mSemWifiManager.setVendorWlanDriverProp(str, str2);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean setDcxoCalibrationData(String str) {
        return this.mSemWifiManager.setDcxoCalibrationData(str);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public String getDcxoCalibrationData() {
        return this.mSemWifiManager.getDcxoCalibrationData();
    }

    private void initAtCommandsView() {
        final String[] strArr = new String[4];
        this.layoutAtCommands = (LinearLayout) findViewById(R.id.at_command_layout);
        this.mInputCmd = (EditText) findViewById(R.id.at_command);
        this.mSendCmd = (Button) findViewById(R.id.send_cmd);
        this.layoutAtCommands.setVisibility(8);
        this.mSendCmd.setOnClickListener(new View.OnClickListener() { // from class: com.sec.android.app.wlantest.WlanTest.38
            @Override // android.view.View.OnClickListener
            public void onClick(View view) {
                if (WlanTest.this.mInputCmd.getText().toString() == null || WlanTest.this.mInputCmd.getText().toString().length() < 4) {
                    Toast.makeText(WlanTest.this, "Enter four parameters", 1).show();
                    return;
                }
                strArr[0] = WlanTest.this.mInputCmd.getText().toString().substring(0, 1);
                strArr[1] = WlanTest.this.mInputCmd.getText().toString().substring(1, 2);
                strArr[2] = WlanTest.this.mInputCmd.getText().toString().substring(2, 3);
                strArr[3] = WlanTest.this.mInputCmd.getText().toString().substring(3);
                WlanTest.this.mInputCmd.setText("");
                WlanTest.this.handleAtCommands(strArr);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void handleAtCommands(String[] strArr) {
        int args = parseArgs(strArr);
        if (args == -1) {
            Log.i("WlanTest", "Error Response NA");
            return;
        }
        CommandArgs commandArgs = new CommandArgs();
        commandArgs.data = strArr[3];
        commandArgs.cmdId = args;
        Log.i("WlanTest", "AT Command ID <" + commandArgs.cmdId + ">, AT Command Data<" + commandArgs.data + "> ");
        Message message = new Message();
        message.what = 262;
        message.obj = commandArgs;
        this.mCommandHandler.sendMessage(message);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void appendBufferedResult(String str, String str2) {
        if ("NG".equals(str)) {
            this.mBufferedResultMessage += "\n" + str2 + " Command failed\n";
            return;
        }
        if ("OK".equals(str)) {
            this.mBufferedResultMessage += "\n" + str2 + " Command completed\n";
        }
    }

    private int parseArgs(String[] strArr) {
        if (checkArgu(strArr, new String[]{"0", "1", "1"})) {
            return 0;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "0"})) {
            return 1;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "1"})) {
            return 2;
        }
        if (checkArgu(strArr, new String[]{"0", "7", "0"})) {
            return 4;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "2"})) {
            return 5;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "0"})) {
            return 6;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "3"})) {
            return 7;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "5"})) {
            return 8;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "4"})) {
            return 9;
        }
        if (checkArgu(strArr, new String[]{"0", "2", "1"})) {
            return 10;
        }
        if (checkArgu(strArr, new String[]{"0", "2", "0"})) {
            return 11;
        }
        if (checkArgu(strArr, new String[]{"0", "3", "1"})) {
            return 12;
        }
        if (checkArgu(strArr, new String[]{"0", "3", "0"})) {
            return 13;
        }
        if (checkArgu(strArr, new String[]{"0", "4", "0"})) {
            return 14;
        }
        if (checkArgu(strArr, new String[]{"0", "4", "1"})) {
            return 15;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "6"})) {
            return 16;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "7"})) {
            return 17;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "3"})) {
            return 18;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "2"})) {
            return 19;
        }
        if (checkArgu(strArr, new String[]{"0", "6", "0"})) {
            return 20;
        }
        if (checkArgu(strArr, new String[]{"0", "6", "1"})) {
            return 21;
        }
        if (checkArgu(strArr, new String[]{"0", "6", "2"})) {
            return 22;
        }
        if (checkArgu(strArr, new String[]{"0", "4", "2"})) {
            return 23;
        }
        if (checkArgu(strArr, new String[]{"0", "4", "3"})) {
            return 25;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "5"})) {
            return 26;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "9"})) {
            return 27;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "6"})) {
            return 28;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "9"})) {
            return 39;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "8"})) {
            return 40;
        }
        if (checkArgu(strArr, new String[]{"1", "0", "0"})) {
            return 41;
        }
        if (checkArgu(strArr, new String[]{"0", "1", "7"})) {
            return 42;
        }
        if (checkArgu(strArr, new String[]{"0", "4", "4"})) {
            return 43;
        }
        if (checkArgu(strArr, new String[]{"0", "4", "5"})) {
            return 44;
        }
        if (checkArgu(strArr, new String[]{"5", "0", "1"})) {
            return 45;
        }
        if (checkArgu(strArr, new String[]{"9", "9", "9"})) {
            return 46;
        }
        if (checkArgu(strArr, new String[]{"0", "2", "2"})) {
            return 47;
        }
        if (checkArgu(strArr, new String[]{"0", "3", "3"})) {
            return 48;
        }
        if (checkArgu(strArr, new String[]{"0", "0", "10"})) {
            return 49;
        }
        if (checkArgu(strArr, new String[]{"4", "1", "4"})) {
            return 51;
        }
        if (checkArgu(strArr, new String[]{"4", "1", "8"})) {
            return 52;
        }
        if (checkArgu(strArr, new String[]{"4", "0", "3"})) {
            return 53;
        }
        if (checkArgu(strArr, new String[]{"4", "0", "4"})) {
            return 54;
        }
        if (checkArgu(strArr, new String[]{"0", "6", "5"})) {
            return 56;
        }
        Toast.makeText(this, "Unsupported Command", 0).show();
        return -1;
    }

    /* JADX DEBUG: Don't trust debug lines info. Repeating lines: [3399=4] */
    /* JADX INFO: Access modifiers changed from: private */
    public int DoShellCmd(String str) {
        Log.d("WlanTest", "cmd = " + str);
        Process processExec = null;
        try {
            try {
                try {
                    processExec = Runtime.getRuntime().exec(new String[]{"/system/bin/sh", "-c", str});
                    processExec.waitFor();
                    BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(processExec.getInputStream(), StandardCharsets.UTF_8));
                    while (true) {
                        String line = bufferedReader.readLine();
                        if (line == null) {
                            Log.d("WlanTest", "exec done");
                            processExec.destroy();
                            return 1;
                        }
                        Log.i("DoShellCmd", line);
                    }
                } catch (SecurityException e) {
                    Log.e("WlanTest", "SecurityException" + e);
                    if (processExec != null) {
                        processExec.destroy();
                    }
                    return -1;
                }
            } catch (IOException e2) {
                Log.e("WlanTest", "DoShellCmd - IOException" + e2);
                if (processExec != null) {
                    processExec.destroy();
                }
                return -1;
            } catch (InterruptedException e3) {
                Log.e("WlanTest", "InterruptedException" + e3);
                if (processExec != null) {
                    processExec.destroy();
                }
                return -1;
            }
        } catch (Throwable th) {
            if (processExec != null) {
                processExec.destroy();
            }
            throw th;
        }
    }

    private boolean checkArgu(String[] strArr, String[] strArr2) {
        for (int i = 0; i < strArr2.length; i++) {
            if (!strArr[i].equalsIgnoreCase(strArr2[i])) {
                return false;
            }
        }
        return true;
    }

    @VisibleForTesting
    String getGriData() {
        Log.d("WlanTest", "griData=" + this.griData);
        return this.griData;
    }

    private String tasModeToString(String str) {
        str.getClass();
        switch (str) {
            case "0":
                return "Legacy SAR";
            case "1":
                return "Vendor proprietary combined TAS";
            case "2":
                return "S-TAS";
            case "3":
                return "C-TAS";
            case "Not updated yet":
                return "Not updated yet. Try to turn on Wifi";
            case "Not supported cmd":
                return "Unknown";
            default:
                return "Invalid TAS mode";
        }
    }
}
