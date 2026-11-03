package com.samsung.android.nfc.nci.cmd.factory;

import com.samsung.android.nfc.nci.SamsungNciPacket;
import java.nio.ByteBuffer;

/* JADX INFO: loaded from: classes.dex */
public class PrbsCommand extends SamsungNciPacket {
    protected PrbsCommand(byte[] bArr) {
        super((byte) 1, bArr);
    }

    public static PrbsCommand create(byte b, byte b2, byte b3) {
        return new PrbsCommand(toPayload(b, b2, b3));
    }

    private static byte[] toPayload(byte b, byte b2, byte b3) {
        ByteBuffer byteBufferPut = ByteBuffer.allocate(b == 1 ? 4 : 2).put((byte) 33).put(b);
        if (b == 1) {
            byteBufferPut.put(b2).put(b3);
        }
        return byteBufferPut.array();
    }
}
