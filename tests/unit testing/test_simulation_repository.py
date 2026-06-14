from app.repositories import SimulationRepository


# UT-30
def test_create_stores_simulation_parameters(app):
    simulation = SimulationRepository.create(
        server_utilization_percent=72,
        horizon_months=6,
        capacity_cpu=500,
        capacity_ram=512,
        capacity_storage=10000,
    )

    assert simulation.simulation_id is not None
    assert simulation.created_at is not None

    fetched = SimulationRepository.get_by_id(simulation.simulation_id)
    assert fetched.server_utilization_percent == 72
    assert fetched.horizon_months == 6
    assert fetched.capacity_cpu == 500
    assert fetched.capacity_ram == 512
    assert fetched.capacity_storage == 10000
