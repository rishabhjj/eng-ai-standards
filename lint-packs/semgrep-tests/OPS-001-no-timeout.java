import java.net.http.HttpClient;
import java.time.Duration;

class Ops001 {
  void f() {
    // ruleid: eng-ai.ops-001.java-httpclient-no-timeout
    HttpClient a = HttpClient.newHttpClient();
    // ruleid: eng-ai.ops-001.java-httpclient-no-timeout
    HttpClient b = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build();
    // ok: eng-ai.ops-001.java-httpclient-no-timeout
    HttpClient c = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
  }
}
