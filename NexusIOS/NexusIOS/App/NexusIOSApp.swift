import SwiftUI

@main
struct NexusIOSApp: App {
    @StateObject private var appState = AppState.shared

    var body: some Scene {
        WindowGroup {
            Group {
                if appState.isCheckingAuth {
                    SplashView()
                } else if appState.isAuthenticated {
                    MainTabView()
                } else {
                    LoginView()
                }
            }
            .environmentObject(appState)
            .task {
                await appState.checkAuth()
            }
        }
    }
}

struct SplashView: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.25, green: 0.22, blue: 0.55),
                    Color(red: 0.05, green: 0.09, blue: 0.22)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
            VStack(spacing: 14) {
                Image("os-logo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 58, height: 72)
                Text("Nexus")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                ProgressView()
                    .tint(.white)
            }
        }
    }
}
