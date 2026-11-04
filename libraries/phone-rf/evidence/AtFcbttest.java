package com.sec.facatfunction.aporiented.athandler;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import com.sec.facatfunction.support.FtUtil;
import com.sec.factorymodule.modules.ModuleCommunication;
import com.sec.xmldata.support.XmlUtil;

/* JADX INFO: compiled from: qb/101698119 0d8887c624184b189bc8b7653cd491643fc7f3f32726e98d7320faeeb999f365 */
/* JADX INFO: loaded from: classes.dex */
public final class AtFcbttest extends AtCommandHandler {
    public String first_argu;

    @Override // com.sec.facatfunction.aporiented.athandler.AtCommandHandler
    public final synchronized String handleCommand(String[] strArr) {
        String str;
        try {
            this.first_argu = strArr[0];
            if (strArr.length != this.NUM_ARGS) {
                AtCommandHandler.responseNA();
                return "\r\n+CME Error:NA\r\n\r\nOK\r\n";
            }
            if (checkArgu(strArr, new String[]{"0", "0", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btActivationWhereAtcmd();
            } else if (checkArgu(strArr, new String[]{"0", "0", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btSearchStart();
            } else if (checkArgu(strArr, new String[]{"0", "1", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btSearchStartWithAck();
            } else if (checkArgu(strArr, new String[]{"0", "1", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btSearchStop();
            } else if (checkArgu(strArr, new String[]{"0", "1", "3"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).bleSearchStartWithAckOn10s();
            } else if (checkArgu(strArr, new String[]{"1", "1", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btREDRxRSSIRead();
            } else if (checkArgu(strArr, new String[]{"1", "1", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btREDTxCalResultRead();
            } else if (checkArgu(strArr, new String[]{"0", "2", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btDeactivation();
            } else if (checkArgu(strArr, new String[]{"0", "3", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btRfTestStart();
            } else if (checkArgu(strArr, new String[]{"0", "2", "1"})) {
                ModuleCommunication.instance(this.context).btRfTestStop();
                FtUtil.Sleep.sleep(500L);
                this.writer.write(responseOK(strArr[0]));
            } else if (checkArgu(strArr, new String[]{"0", "4", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btAudioTestStart();
            } else if (checkArgu(strArr, new String[]{"0", "2", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btAudioTestStop();
            } else if (checkArgu(strArr, new String[]{"0", "5", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxOutputChLow();
            } else if (checkArgu(strArr, new String[]{"0", "5", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxOutputChMid();
            } else if (checkArgu(strArr, new String[]{"0", "5", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxOutputChHigh();
            } else if (checkArgu(strArr, new String[]{"0", "5", "3"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxModChLow();
            } else if (checkArgu(strArr, new String[]{"0", "5", "4"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxModChMid();
            } else if (checkArgu(strArr, new String[]{"0", "5", "5"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxModChHigh();
            } else if (checkArgu(strArr, new String[]{"0", "5", "6"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxModChLowAA();
            } else if (checkArgu(strArr, new String[]{"0", "5", "7"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxModChMidAA();
            } else if (checkArgu(strArr, new String[]{"0", "5", "8"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxModChHighAA();
            } else if (checkArgu(strArr, new String[]{"0", "6", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxCarrierChLow();
            } else if (checkArgu(strArr, new String[]{"0", "6", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxCarrierChMid();
            } else if (checkArgu(strArr, new String[]{"0", "6", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxCarrierChHigh();
            } else if (checkArgu(strArr, new String[]{"0", "6", "3"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxInBandChLow();
            } else if (checkArgu(strArr, new String[]{"0", "6", "4"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxInBandChMid();
            } else if (checkArgu(strArr, new String[]{"0", "6", "5"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTxInBandChHigh();
            } else if (checkArgu(strArr, new String[]{"0", "6", "6"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeRxLow();
            } else if (checkArgu(strArr, new String[]{"0", "6", "7"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeRxMid();
            } else if (checkArgu(strArr, new String[]{"0", "6", "8"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeRxHigh();
            } else if (checkArgu(strArr, new String[]{"0", "6", "9"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTestEnd();
            } else if (checkArgu(strArr, new String[]{"0", "7", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btEdrTxLow();
            } else if (checkArgu(strArr, new String[]{"0", "7", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btEdrTxMid();
            } else if (checkArgu(strArr, new String[]{"0", "7", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btEdrTxHigh();
            } else if (checkArgu(strArr, new String[]{"0", "7", "3"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btAntSwitchEdrTxMid();
            } else if (checkArgu(strArr, new String[]{"0", "8", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btEdrRxLow();
            } else if (checkArgu(strArr, new String[]{"0", "8", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btEdrRxMid();
            } else if (checkArgu(strArr, new String[]{"0", "8", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btEdrRxHigh();
            } else if (checkArgu(strArr, new String[]{"0", "8", "3"})) {
                startReceiver();
                ModuleCommunication moduleCommunicationInstance = ModuleCommunication.instance(this.context);
                XmlUtil.log_i(moduleCommunicationInstance.CLASS_NAME, "btBrEdrTestEnd", "btBrEdrTestEnd()");
                moduleCommunicationInstance.requestActionToBTService(36);
            } else if (checkArgu(strArr, new String[]{"0", "9", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btHpmLowPath();
            } else if (checkArgu(strArr, new String[]{"0", "9", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btHpmHighPath();
            } else if (checkArgu(strArr, new String[]{"1", "9", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btHpmReadPath();
            } else if (checkArgu(strArr, new String[]{"1", "9", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTestRead();
            } else if (checkArgu(strArr, new String[]{"3", "0", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btBrTxLow();
            } else if (checkArgu(strArr, new String[]{"3", "0", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btBrTxMid();
            } else if (checkArgu(strArr, new String[]{"3", "0", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btBrTxHigh();
            } else if (checkArgu(strArr, new String[]{"3", "1", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btBrRxLow();
            } else if (checkArgu(strArr, new String[]{"3", "1", "1"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btBrRxMid();
            } else if (checkArgu(strArr, new String[]{"3", "1", "2"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btBrRxHigh();
            } else if (checkArgu(strArr, new String[]{"3", "1", "3"})) {
                startReceiver();
                ModuleCommunication moduleCommunicationInstance2 = ModuleCommunication.instance(this.context);
                XmlUtil.log_i(moduleCommunicationInstance2.CLASS_NAME, "btBrEdrTestEnd", "btBrEdrTestEnd()");
                moduleCommunicationInstance2.requestActionToBTService(36);
            } else if (checkArgu(strArr, new String[]{"3", "4", "0"})) {
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTest1M();
            } else {
                if (!checkArgu(strArr, new String[]{"3", "4", "1"})) {
                    if (checkArgu(strArr, new String[]{"4", "0"})) {
                        try {
                            int i = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtSignalSelect(i);
                        } catch (NumberFormatException unused) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused2) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "1"})) {
                        try {
                            int i2 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtCoreSelect(i2);
                        } catch (NumberFormatException unused3) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused4) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "2"})) {
                        try {
                            int i3 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtChannel(i3);
                        } catch (NumberFormatException unused5) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused6) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "3"})) {
                        try {
                            int i4 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtDataRate(i4);
                        } catch (NumberFormatException unused7) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused8) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "4"})) {
                        try {
                            int i5 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtTxPower(i5);
                        } catch (NumberFormatException unused9) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused10) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "5"})) {
                        try {
                            int i6 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtPaMode(i6);
                        } catch (NumberFormatException unused11) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused12) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "6"})) {
                        try {
                            int i7 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtPacketType(i7);
                        } catch (NumberFormatException unused13) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused14) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "7"})) {
                        try {
                            int i8 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtAclFrame(i8);
                        } catch (NumberFormatException unused15) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused16) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "8"})) {
                        try {
                            int i9 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtTxStartStop(i9);
                        } catch (NumberFormatException unused17) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused18) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "9"})) {
                        try {
                            int i10 = Integer.parseInt(strArr[2]);
                            startReceiver();
                            ModuleCommunication.instance(this.context).dualBtRxStartStop(i10);
                        } catch (NumberFormatException unused19) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        } catch (Exception unused20) {
                            AtCommandHandler.responseNA();
                            str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                        }
                    } else if (checkArgu(strArr, new String[]{"4", "10", "0"})) {
                        startReceiver();
                        ModuleCommunication.instance(this.context).dualBtRxGoodpacket();
                    } else {
                        AtCommandHandler.responseNA();
                        str = "\r\n+CME Error:NA\r\n\r\nOK\r\n";
                    }
                    return str;
                }
                startReceiver();
                ModuleCommunication.instance(this.context).btLeTest2M();
            }
            str = null;
            return str;
        } catch (Throwable th) {
            throw th;
        }
    }

    public final void startReceiver() {
        this.context.registerReceiver(new BroadcastReceiver() { // from class: com.sec.facatfunction.aporiented.athandler.AtFcbttest.1
            @Override // android.content.BroadcastReceiver
            public final void onReceive(Context context, Intent intent) {
                if ("com.sec.factory.intent.ACTION_BT_SERVICE_RESPONSE".equals(intent.getAction())) {
                    String stringExtra = intent.getStringExtra("result");
                    AtApchiptt$$ExternalSyntheticOutline0.m("EXTRA_KEY_BT_SERVICE_RESPONSE result=", stringExtra, AtFcbttest.this.CLASS_NAME, "btReceiver.onReceive");
                    AtFcbttest atFcbttest = AtFcbttest.this;
                    atFcbttest.writer.write(atFcbttest.responseString(atFcbttest.first_argu, stringExtra));
                    AtFcbttest.this.stopReceiver(this);
                }
            }
        }, new IntentFilter("com.sec.factory.intent.ACTION_BT_SERVICE_RESPONSE"), 2);
    }
}
