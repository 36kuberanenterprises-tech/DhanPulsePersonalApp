package `in`.dhanpulse.personal.data

import `in`.dhanpulse.personal.model.*
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

interface DhanPulseApi {
    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    @GET("api/analysis/{symbol}")
    suspend fun analysis(
        @Header("X-Session-Id") sessionId: String,
        @Path("symbol") symbol: String,
        @Query("interval") interval: String = "FIVE_MINUTE"
    ): AnalysisResponse

    @POST("api/auth/logout")
    suspend fun logout(@Header("X-Session-Id") sessionId: String): Map<String, Any>
}

object ApiFactory {
    fun create(baseUrl: String): DhanPulseApi {
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .addInterceptor(Interceptor { chain ->
                chain.proceed(chain.request().newBuilder().header("Accept", "application/json").build())
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
