package `in`.dhanpulse.personal.data

import `in`.dhanpulse.personal.model.*
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface DhanPulseApi {
    @GET("health")
    suspend fun health(): BackendHealth

    @GET("api/auth/readiness")
    suspend fun loginReadiness(): BackendHealth

    @GET("api/flow/catalog")
    suspend fun flowCatalog(@Header("X-Session-Id") sessionId:String, @Query("group") group:String,
        @Query("q") query:String, @Query("guided") guided:Boolean=true,
        @Query("underlying") underlying:String="", @Query("kind") kind:String="",
        @Query("expiry") expiry:String="", @Query("offset") offset:Int=0): `in`.dhanpulse.personal.FlowCatalog

    @GET("api/flow/monitor")
    suspend fun flowMonitor(@Header("X-Session-Id") sessionId:String, @Query("exchange") exchange:String,
        @Query("token") token:String, @Query("minutes") minutes:Int,
        @Query("restart") restart:Boolean=false): `in`.dhanpulse.personal.FlowSnapshot

    @GET("api/markets/mcx")
    suspend fun mcxMarkets(@Header("X-Session-Id") sessionId: String): McxCatalog

    @GET("api/stocks/scanner")
    suspend fun stockScanner(
        @Header("X-Session-Id") sessionId: String,
        @Query("trackedToken") trackedToken: String? = null
    ): StockScanResponse

    @GET("api/stocks/live-movers")
    suspend fun liveMovers(
        @Header("X-Session-Id") sessionId: String,
        @Query("refresh") refresh: Boolean = false
    ): LiveMoversResponse

    @GET("api/stocks/keep-eye")
    suspend fun keepEyeScanner(
        @Header("X-Session-Id") sessionId: String,
        @Query("refresh") refresh: Boolean = false
    ): KeepEyeScanResponse

    @GET("api/stocks/opportunity")
    suspend fun stockOpportunity(@Header("X-Session-Id") sessionId: String): StockOpportunity

    @GET("api/stocks/options/catalog")
    suspend fun stockOptionCatalog(@Header("X-Session-Id") sessionId: String): StockOptionCatalog

    @GET("api/stocks/options/{symbol}")
    suspend fun stockOptions(@Header("X-Session-Id") sessionId: String, @Path("symbol") symbol: String): StockOptionSnapshot

    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    @GET("api/analysis/{symbol}")
    suspend fun analysis(
        @Header("X-Session-Id") sessionId: String,
        @Path("symbol") symbol: String,
        @Query("interval") interval: String = "FIVE_MINUTE",
        @Query("trackedToken") trackedToken: String? = null
    ): AnalysisResponse

    @GET("api/account")
    suspend fun account(
        @Header("X-Session-Id") sessionId: String
    ): AccountSummary

    @POST("api/backtest")
    suspend fun backtest(
        @Header("X-Session-Id") sessionId: String,
        @Body request: BacktestRequest
    ): BacktestReport

    @GET("api/backtest/catalog")
    suspend fun backtestCatalog(@Header("X-Session-Id") sessionId: String): BacktestCatalog

    @GET("api/order/diagnostics")
    suspend fun orderDiagnostics(
        @Header("X-Session-Id") sessionId: String
    ): OrderGatewayDiagnostics

    @POST("api/order")
    suspend fun placeOrder(
        @Header("X-Session-Id") sessionId: String,
        @Body request: OrderRequest
    ): OrderResponse

    @POST("api/auth/logout")
    suspend fun logout(@Header("X-Session-Id") sessionId: String): Map<String, Any>
}

object ApiFactory {
    fun create(baseUrl: String): DhanPulseApi {
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        // Do not print private endpoint, broker requests or login URLs to Logcat.\n        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.NONE }
        val client = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .callTimeout(210, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .addInterceptor(Interceptor { chain ->
                val request = chain.request()
                // Reachability uses a credential-free GET so a sleeping backend
                // cannot consume or expire the user's one-time TOTP.
                if (request.url.encodedPath == "/health") {
                    chain.call().timeout().timeout(30, TimeUnit.SECONDS)
                } else if (request.url.encodedPath == "/api/auth/login") {
                    chain.call().timeout().timeout(30, TimeUnit.SECONDS)
                }
                val builder = request.newBuilder().header("Accept", "application/json")
                if (request.url.encodedPath.startsWith("/api/analysis/")) {
                    val policy = if (request.url.pathSegments.lastOrNull()?.equals("SENSEX", ignoreCase = true) == true)
                        "sensex-dual-v1" else "oi-caution-v1"
                    builder.header("X-DhanPulse-Analysis-Policy", policy)
                }
                val boundedChain = if (request.url.encodedPath.contains("backtest"))
                    chain.withReadTimeout(180, TimeUnit.SECONDS) else chain
                boundedChain.proceed(builder.build())
            })
            .build()
        return Retrofit.Builder()
            .baseUrl(normalized)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(DhanPulseApi::class.java)
    }
}
