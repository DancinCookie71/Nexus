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
        VStack(spacing: 16) {
            Text("Nexus")
                .font(.largeTitle.weight(.bold))
            ProgressView()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemGroupedBackground))
    }
}
