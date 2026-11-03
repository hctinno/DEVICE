package com.sec.facatfunction.aporiented.athandler;

import android.content.Intent;
import android.content.IntentFilter;
import com.sec.facatfunction.support.FtUtil;
import com.sec.xmldata.support.Support$Path;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public final class AtWifitest extends AtCommandHandler {
    public String first_argu;
    public boolean isReceivedATCommands;
    public AnonymousClass1 mReceiver;
    public int mWlanTest;
    public String[] savedArgu;

    @Override // com.sec.facatfunction.aporiented.athandler.AtCommandHandler
    public final synchronized String handleCommand(String[] strArr) {
        String strResponseOK;
        try {
            StringBuilder sb = new StringBuilder();
            for (String str : strArr) {
                sb.append(str);
            }
            FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : " + ((Object) sb));
            if (strArr.length != this.NUM_ARGS && strArr.length != 12) {
                AtCommandHandler.responseNA();
                return "\r\n+CME Error:NA\r\n\r\nOK\r\n";
            }
            this.first_argu = strArr[0];
            if (checkArgu(strArr, new String[]{"3", "8", "0", "0"})) {
                Support$Path.writeNsync("AIR_COMMAND_WIFI", "0");
                return responseOK(strArr[0]);
            }
            if (checkArgu(strArr, new String[]{"3", "8", "0", "1"})) {
                Support$Path.writeNsync("AIR_COMMAND_WIFI", "1");
                return responseOK(strArr[0]);
            }
            if (checkArgu(strArr, new String[]{"3", "8", "0", "2"})) {
                return responseOK(strArr[0]);
            }
            FtUtil.log_d(this.CLASS_NAME, "handleCommand", "mWlanTest: " + this.mWlanTest);
            this.isReceivedATCommands = true;
            if (this.mWlanTest != 0) {
                startReceiver();
                if (checkArgu(strArr, new String[]{"0", "1", "0"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : closeDut");
                    sendIntent(1, strArr[3]);
                    this.mWlanTest = 0;
                } else if (checkArgu(strArr, new String[]{"0", "1", "1"})) {
                    String str2 = strArr[3];
                    if ("1".equals(str2)) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : openDut(No response)");
                        stopReceiver(this.mReceiver);
                        str2 = "0";
                    } else {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : openDut");
                    }
                    sendIntent(0, str2);
                } else if (checkArgu(strArr, new String[]{"0", "1", "2"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : unloadNormalFW");
                    sendIntent(19, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "1", "3"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : loadNormalFW");
                    sendIntent(18, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "1", "5"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Channel Encoding");
                    sendIntent(26, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "1", "6"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : RU Base Rx Test Setting");
                    sendIntent(28, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "1", "7"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : C-RED Setting (On / Off)");
                    sendIntent(42, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "1", "8"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Set Country");
                    sendIntent(40, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "1", "9"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Get Country");
                    sendIntent(39, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "0"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : channelSetting");
                    sendIntent(6, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "1"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : dataRateSetting");
                    sendIntent(2, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "2"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : preambleSetting");
                    sendIntent(5, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "3"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : txGainSetting");
                    sendIntent(7, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "4"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : payloadLengthSetting");
                    sendIntent(9, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "5"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : burstIntervalSetting");
                    sendIntent(8, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "6"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : BandSetting");
                    sendIntent(16, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "7"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : BandwidthSetting");
                    sendIntent(17, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "9"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : RU");
                    sendIntent(27, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "0", "10"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : nonOFDMAMRU");
                    sendIntent(49, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "2", "0"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : stopTx");
                    sendIntent(11, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "2", "1"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : startTx");
                    sendIntent(10, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "2", "2"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Link1/Link2 Start Tx");
                    sendIntent(47, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "3", "0"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : stopRx");
                    sendIntent(13, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "3", "1"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : startRx");
                    sendIntent(12, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "3", "3"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Link1/Link2 Start Rx");
                    sendIntent(48, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "4", "0"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : rxFrameReceiveError");
                    sendIntent(14, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "4", "1"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : rxFrameReceiveGood");
                    sendIntent(15, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "4", "2"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : GetRSSI");
                    sendIntent(23, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "4", "3"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : GetRED");
                    sendIntent(25, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "4", "4"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Close Loop Power Control TSSI Test");
                    sendIntent(43, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "4", "5"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : 11ax Tx Error");
                    sendIntent(44, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "6", "0"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : joinAP");
                    sendIntent(20, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "6", "1"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : joinAP with 2GHz");
                    sendIntent(21, strArr[3]);
                } else if (checkArgu(strArr, new String[]{"0", "6", "2"})) {
                    FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : joinAP with 5GHz");
                    sendIntent(22, strArr[3]);
                } else {
                    if (checkArgu(strArr, new String[]{"0", "7", "0"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Ant Select");
                        sendIntent(4, strArr[3]);
                    } else if (checkArgu(strArr, new String[]{"0", "9", "9"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Set All settings");
                        StringBuilder sb2 = new StringBuilder(strArr[3]);
                        int length = strArr.length - 1;
                        for (int i = 4; i < length; i++) {
                            sb2.append(",");
                            sb2.append(strArr[i]);
                        }
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "dataArgu : " + ((Object) sb2));
                        sendIntent(24, sb2.toString());
                    } else if (checkArgu(strArr, new String[]{"1", "0", "0"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Get Module Vendor");
                        sendIntent(41, strArr[3]);
                    } else if (checkArgu(strArr, new String[]{"4", "1", "4"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : RX Cal Start");
                        sendIntent(51, strArr[3]);
                    } else if (checkArgu(strArr, new String[]{"4", "1", "8"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Get Freq Cal Data");
                        sendIntent(52, strArr[3]);
                    } else if (checkArgu(strArr, new String[]{"4", "0", "3"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Write CapTune, Temperature");
                        sendIntent(53, strArr[3]);
                    } else if (checkArgu(strArr, new String[]{"4", "0", "4"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Read CapTune, Temperature");
                        sendIntent(54, strArr[3]);
                    } else if (checkArgu(strArr, new String[]{"5", "0", "1"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Get Rx IQEST");
                        sendIntent(45, strArr[3]);
                    } else if (checkArgu(strArr, new String[]{"9", "9", "9"})) {
                        FtUtil.log_d(this.CLASS_NAME, "handleCommand", "command : Start test mode");
                        sendIntent(46, strArr[3]);
                    } else {
                        AtCommandHandler.responseNA();
                        strResponseOK = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                    }
                }
                strResponseOK = null;
            } else if (checkArgu(strArr, new String[]{"0", "1", "0"}) || checkArgu(strArr, new String[]{"0", "1", "2"})) {
                strResponseOK = responseOK(strArr[0]);
            } else {
                startReceiver();
                this.savedArgu = strArr;
                Intent intent = new Intent();
                intent.setClassName("com.sec.android.app.wlantest", "com.sec.android.app.wlantest.WlanTest");
                intent.setFlags(268435456);
                intent.putExtra("MODE", "auto");
                this.context.startActivity(intent);
                strResponseOK = null;
            }
            return strResponseOK;
        } catch (Throwable th) {
            throw th;
        }
    }

    public final void sendIntent(int i, String str) {
        if (this.mWlanTest == 1) {
            Intent intent = new Intent("com.sec.android.app.wlantest.WIFI_TEST_INDICATION");
            intent.putExtra("CMDID", i);
            intent.putExtra("S_DATA", str);
            intent.putExtra("BYPASS", 0);
            this.context.sendBroadcast(intent);
        }
    }

    public final void startReceiver() {
        FtUtil.log_i(this.CLASS_NAME, "startReceiver");
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction("com.sec.android.app.wlantest.WIFI_TEST_RESPONSE");
        intentFilter.addAction("android.intent.action.WIFI_DRIVER_INDICATION");
        this.context.registerReceiver(this.mReceiver, intentFilter, 2);
    }
}
