from app.simulation.metrics import city_metrics, mobility_metrics, population_metrics, safety_metrics
from app.simulation.world import World

def test_metric_modules_preserve_dashboard_contract():
    world=World(seed=7070,citizen_count=100)
    metrics=city_metrics(world)
    required={"population","unemploymentRate","medianRent","medicalEmergencies","activeIncidents","averageTripMinutes","friendships"}
    assert required <= metrics.keys()
    assert metrics["population"]==100

def test_metric_modules_are_safe_before_activity_starts():
    world=World(seed=7071,citizen_count=10)
    assert population_metrics(world)["averageJobPerformance"] >= 0
    assert mobility_metrics(world)["averageTripMinutes"] == 0
    assert safety_metrics(world)["averagePoliceResponseMinutes"] == 0
