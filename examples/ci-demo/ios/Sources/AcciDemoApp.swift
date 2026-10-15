import SwiftUI

enum Calc {
    static func mul(_ a: Int, _ b: Int) -> Int { a * b }
}

struct EnergyCounter {
    private(set) var score = 0
    mutating func collect() { score = min(score + 1, 9999) }
    mutating func reset() { score = 0 }
}

struct DemoView: View {
    @State private var counter = EnergyCounter()

    var body: some View {
        VStack(spacing: 24) {
            Text("ACCI Demo: 6 × 7 = \(Calc.mul(6, 7))")
                .font(.title)
                .accessibilityIdentifier("calculation")
            Text("Energy: \(counter.score)")
                .font(.title2)
                .accessibilityIdentifier("score")
            Button("Collect energy") { counter.collect() }
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("collect")
            Button("Reset") { counter.reset() }
                .accessibilityIdentifier("reset")
        }
        .padding()
    }
}

@main
struct AcciDemoApp: App {
    var body: some Scene {
        WindowGroup {
            DemoView()
        }
    }
}
