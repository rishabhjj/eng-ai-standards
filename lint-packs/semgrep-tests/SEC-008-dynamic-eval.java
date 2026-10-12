import java.io.InputStream;
import java.io.ObjectInputStream;

class Sec008 {
  void f(InputStream in) throws Exception {
    // ruleid: eng-ai.sec-008.java-native-deserialization
    new ObjectInputStream(in);
    // ruleid: eng-ai.sec-008.java-native-deserialization
    new java.io.ObjectInputStream(in);
    // ok: eng-ai.sec-008.java-native-deserialization
    new java.io.DataInputStream(in);
  }
}
