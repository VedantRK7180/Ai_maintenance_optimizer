# ================================================================
# AI MAINTENANCE OPTIMIZER
# GENETIC ALGORITHM SCHEDULER
# ================================================================

import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()
import random
from datetime import datetime, time, timedelta


# ================================================================
# DATABASE CONNECTION
# ================================================================

def connect_db():
    try:
        password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
        if not password:
            raise RuntimeError(
                "MySQL password is missing. Set MYSQL_PASSWORD (or DB_PASSWORD) in .env."
            )

        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost")),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", os.getenv("DB_USER", "root")),
            password=password,
            database=os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "AI_Maintenance_DB")),
        )

        print("Successfully connected to MySQL!")
        return connection

    except mysql.connector.Error as error:
        print("Database connection failed:", error)
        return None


# ================================================================
# GET MAINTENANCE JOBS
# ================================================================

def get_jobs(connection):

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        m.maintenance_id,
        m.machine_id,
        m.technician_id,
        m.maintenance_type,
        m.scheduled_date,
        m.start_time,
        m.end_time,
        m.status,
        m.priority,
        m.notes,

        mc.machine_name,
        mc.criticality,
        mc.production_importance,

        mt.machine_type_id,
        mt.type_name

    FROM MAINTENANCE m

    JOIN MACHINE mc
        ON m.machine_id = mc.machine_id

    JOIN MACHINE_TYPE mt
        ON mc.machine_type_id = mt.machine_type_id

    WHERE m.status = 'Planned'

    ORDER BY m.maintenance_id;
    """

    cursor.execute(query)

    jobs = cursor.fetchall()

    cursor.close()

    return jobs


# ================================================================
# GET LATEST AI DECISIONS
# ================================================================

def get_latest_ai_decisions(connection):

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT d.*
    FROM AI_DECISION d

    INNER JOIN (
        SELECT
            machine_id,
            MAX(decision_time) AS latest_time
        FROM AI_DECISION
        GROUP BY machine_id
    ) latest

    ON d.machine_id = latest.machine_id
    AND d.decision_time = latest.latest_time;
    """

    cursor.execute(query)

    rows = cursor.fetchall()

    cursor.close()

    decisions = {}

    for row in rows:
        decisions[row["machine_id"]] = row

    return decisions


# ================================================================
# GET TECHNICIANS
# ================================================================

def get_technicians(connection):

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        technician_id,
        technician_name,
        specialization,
        availability_status
    FROM TECHNICIAN
    WHERE availability_status = 'Available';
    """

    cursor.execute(query)

    technicians = cursor.fetchall()

    cursor.close()

    return technicians


# ================================================================
# GET MAINTENANCE REQUIREMENTS
# ================================================================

def get_requirements(connection):

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        requirement_id,
        maintenance_type,
        machine_type_id,
        spare_part_id,
        required_quantity,
        estimated_duration_hours
    FROM MAINTENANCE_REQUIREMENT;
    """

    cursor.execute(query)

    requirements = cursor.fetchall()

    cursor.close()

    return requirements


# ================================================================
# GET SPARE PARTS
# ================================================================

def get_spares(connection):

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        spare_part_id,
        part_name,
        machine_type_id,
        quantity_available
    FROM SPARE_PART;
    """

    cursor.execute(query)

    spares = cursor.fetchall()

    cursor.close()

    return spares


# ================================================================
# TIME CONVERSION
# ================================================================

def time_to_minutes(value):

    if value is None:
        return 0

    if isinstance(value, time):

        return (
            value.hour * 60
            + value.minute
            + value.second / 60
        )

    if isinstance(value, timedelta):

        return int(value.total_seconds() / 60)

    if isinstance(value, datetime):

        return value.hour * 60 + value.minute

    if isinstance(value, str):

        parts = value.split(":")

        hour = int(parts[0])
        minute = int(parts[1])

        return hour * 60 + minute

    return 0


# ================================================================
# FORMAT TIME
# ================================================================

def format_time(minutes):

    minutes = int(minutes)

    hour = minutes // 60
    minute = minutes % 60

    return f"{hour:02d}:{minute:02d}"


# ================================================================
# GET JOB DURATION
# ================================================================

def get_duration(job):

    start = time_to_minutes(job["start_time"])
    end = time_to_minutes(job["end_time"])

    duration = end - start

    if duration <= 0:
        duration = 60

    return duration


# ================================================================
# SPECIALIZATION MATCH
# ================================================================

def specialization_matches(job, technician):

    machine_type = job["type_name"].lower()
    specialization = technician["specialization"].lower()

    if "cnc" in machine_type:
        return "cnc" in specialization

    if "robot" in machine_type:
        return "robot" in specialization

    if "rotating" in machine_type:
        return "rotating" in specialization

    return True


# ================================================================
# PRIORITY SCORE
# ================================================================

def priority_score(priority):

    mapping = {
        "Low": 20,
        "Medium": 50,
        "High": 80,
        "Critical": 100
    }

    return mapping.get(priority, 50)


# ================================================================
# CRITICALITY SCORE
# ================================================================

def criticality_score(criticality):

    mapping = {
        "Low": 20,
        "Medium": 50,
        "High": 80,
        "Critical": 100
    }

    return mapping.get(criticality, 50)


# ================================================================
# AI PRIORITY
# ================================================================

def calculate_ai_priority(job, ai_decisions):

    decision = ai_decisions.get(job["machine_id"])

    if decision is None:
        return 0.0

    failure_risk = float(decision["failure_risk"])
    urgency_score = float(decision["urgency_score"])

    return (
        0.6 * failure_risk
        + 0.4 * urgency_score
    )


# ================================================================
# CHECK TECHNICIAN TIME CONFLICT
# ================================================================

def has_time_conflict(
    technician_id,
    start,
    end,
    chromosome,
    jobs,
    technicians
):

    for job_index, assignment in enumerate(chromosome):

        if assignment is None:
            continue

        if job_index >= len(jobs):
            continue

        assigned_technician_id = assignment[0]
        assigned_start = assignment[1]

        if assigned_technician_id != technician_id:
            continue

        assigned_end = assigned_start + get_duration(
            jobs[job_index]
        )

        # Correct overlap condition
        if start < assigned_end and assigned_start < end:

            return True

    return False


# ================================================================
# FIND TECHNICIAN
# ================================================================

def get_technician(technicians, technician_id):

    for technician in technicians:

        if technician["technician_id"] == technician_id:
            return technician

    return None


# ================================================================
# SPARE REQUIREMENT
# ================================================================

def get_job_requirement(job, requirements):

    for requirement in requirements:

        if (
            requirement["maintenance_type"]
            == job["maintenance_type"]
            and
            requirement["machine_type_id"]
            == job["machine_type_id"]
        ):

            return requirement

    return None


# ================================================================
# CHECK SPARE AVAILABILITY
# ================================================================

def spare_available(
    job,
    requirements,
    spares,
    reserved_counts
):

    requirement = get_job_requirement(
        job,
        requirements
    )

    if requirement is None:
        return True

    spare_id = requirement["spare_part_id"]

    required_quantity = requirement["required_quantity"]

    for spare in spares:

        if spare["spare_part_id"] == spare_id:

            available = (
                spare["quantity_available"]
                - reserved_counts.get(spare_id, 0)
            )

            return available >= required_quantity

    return False



# ================================================================
# HARD SPARE-PART CONSTRAINT FILTER
# ================================================================

def filter_jobs_by_spare_availability(
    jobs,
    requirements,
    spares,
    ai_decisions
):
    """
    Split maintenance jobs into:
    1. jobs that have enough spare stock and may enter the GA
    2. jobs blocked because required spare stock is insufficient

    Spare availability is treated as a HARD constraint.
    """

    eligible_jobs = []
    blocked_jobs = []

    # Higher-priority jobs get first claim on limited spare stock.
    ordered_jobs = sorted(
        jobs,
        key=lambda job: (
            -calculate_ai_priority(
                job,
                ai_decisions
            ),
            -priority_score(
                job["priority"]
            ),
            -criticality_score(
                job["criticality"]
            )
        )
    )

    reserved_counts = {}

    for job in ordered_jobs:

        requirement = get_job_requirement(
            job,
            requirements
        )

        if requirement is None:
            eligible_jobs.append(job)
            continue

        spare_id = requirement["spare_part_id"]
        required_quantity = requirement["required_quantity"]

        available_quantity = 0

        for spare in spares:

            if spare["spare_part_id"] == spare_id:

                available_quantity = (
                    spare["quantity_available"]
                )

                break

        already_reserved = reserved_counts.get(
            spare_id,
            0
        )

        remaining_quantity = (
            available_quantity
            - already_reserved
        )

        if remaining_quantity >= required_quantity:

            eligible_jobs.append(job)

            reserved_counts[spare_id] = (
                already_reserved
                + required_quantity
            )

        else:

            blocked_jobs.append(
                {
                    "job": job,
                    "spare_part_id": spare_id,
                    "required_quantity": required_quantity,
                    "available_quantity": available_quantity,
                    "remaining_quantity": max(
                        remaining_quantity,
                        0
                    )
                }
            )

    return (
        eligible_jobs,
        blocked_jobs
    )


# ================================================================
# FITNESS FUNCTION
# ================================================================

def fitness(
    chromosome,
    jobs,
    technicians,
    ai_decisions,
    requirements,
    spares
):

    score = 0

    reserved_counts = {}

    for job_index, job in enumerate(jobs):

        assignment = chromosome[job_index]

        if assignment is None:

            score -= 20000

            continue

        technician_id = assignment[0]
        start = assignment[1]

        technician = get_technician(
            technicians,
            technician_id
        )

        if technician is None:

            score -= 20000

            continue

        duration = get_duration(job)

        end = start + duration

        # --------------------------------------------------------
        # Working hours
        # --------------------------------------------------------

        if start < 9 * 60 or end > 18 * 60:

            score -= 15000

        # --------------------------------------------------------
        # Technician availability
        # --------------------------------------------------------

        if technician["availability_status"] == "Available":
            score += 20
        else:
            score -= 10000

        # --------------------------------------------------------
        # Specialization
        # --------------------------------------------------------

        if specialization_matches(
            job,
            technician
        ):

            score += 100

        else:

            score -= 500

        # --------------------------------------------------------
        # AI priority
        # --------------------------------------------------------

        ai_priority = calculate_ai_priority(
            job,
            ai_decisions
        )

        score += ai_priority

        # --------------------------------------------------------
        # Maintenance priority
        # --------------------------------------------------------

        score += priority_score(
            job["priority"]
        )

        # --------------------------------------------------------
        # Machine criticality
        # --------------------------------------------------------

        score += criticality_score(
            job["criticality"]
        ) * 0.5

        # --------------------------------------------------------
        # Spare availability
        # --------------------------------------------------------

        requirement = get_job_requirement(
            job,
            requirements
        )

        if requirement is not None:

            spare_id = requirement["spare_part_id"]

            reserved_counts[spare_id] = (
                reserved_counts.get(spare_id, 0)
                + requirement["required_quantity"]
            )

    # ============================================================
    # CHECK TECHNICIAN CONFLICTS
    # ============================================================

    for i in range(len(jobs)):

        if chromosome[i] is None:
            continue

        technician_i = chromosome[i][0]
        start_i = chromosome[i][1]
        end_i = start_i + get_duration(jobs[i])

        for j in range(i + 1, len(jobs)):

            if chromosome[j] is None:
                continue

            technician_j = chromosome[j][0]
            start_j = chromosome[j][1]
            end_j = start_j + get_duration(jobs[j])

            if technician_i == technician_j:

                if (
                    start_i < end_j
                    and
                    start_j < end_i
                ):

                    score -= 15000

    # ============================================================
    # PREFER ORIGINAL TIME
    # ============================================================

    for job_index, job in enumerate(jobs):

        if chromosome[job_index] is None:
            continue

        original_start = time_to_minutes(
            job["start_time"]
        )

        actual_start = chromosome[job_index][1]

        difference = abs(
            original_start - actual_start
        )

        # Small penalty for moving jobs
        score -= difference * 0.05

    return score


# ================================================================
# CREATE RANDOM CHROMOSOME
# ================================================================

def create_random_chromosome(
    jobs,
    technicians
):

    chromosome = []

    for job in jobs:

        possible_technicians = [
            technician
            for technician in technicians
            if specialization_matches(
                job,
                technician
            )
        ]

        # If no specialist exists, allow any technician
        if not possible_technicians:

            possible_technicians = technicians

        technician = random.choice(
            possible_technicians
        )

        original_start = time_to_minutes(
            job["start_time"]
        )

        duration = get_duration(job)

        possible_starts = []

        for start in range(
            9 * 60,
            18 * 60 - duration + 1,
            30
        ):

            possible_starts.append(start)

        if possible_starts:

            # Usually start near original time
            nearby = [
                start
                for start in possible_starts
                if abs(start - original_start) <= 120
            ]

            if nearby:

                start_time = random.choice(
                    nearby
                )

            else:

                start_time = random.choice(
                    possible_starts
                )

        else:

            start_time = 9 * 60

        chromosome.append(
            (
                technician["technician_id"],
                start_time
            )
        )

    return chromosome


# ================================================================
# FEASIBLE ASSIGNMENT SEARCH
# ================================================================

def find_feasible_assignment(
    jobs,
    technicians,
    job_order
):

    chromosome = [
        None
        for _ in jobs
    ]

    def backtrack(position):

        if position >= len(job_order):

            return True

        job_index = job_order[position]

        job = jobs[job_index]

        duration = get_duration(job)

        original_start = time_to_minutes(
            job["start_time"]
        )

        # --------------------------------------------------------
        # Sort technicians:
        # specialists first
        # --------------------------------------------------------

        sorted_technicians = sorted(
            technicians,
            key=lambda technician: (
                not specialization_matches(
                    job,
                    technician
                )
            )
        )

        # --------------------------------------------------------
        # Create possible time slots
        # --------------------------------------------------------

        possible_starts = list(
            range(
                9 * 60,
                18 * 60 - duration + 1,
                30
            )
        )

        # Prefer original time first
        possible_starts.sort(
            key=lambda start: abs(
                start - original_start
            )
        )

        # --------------------------------------------------------
        # Try every technician and time
        # --------------------------------------------------------

        for technician in sorted_technicians:

            technician_id = technician["technician_id"]

            for start in possible_starts:

                end = start + duration

                conflict = has_time_conflict(
                    technician_id,
                    start,
                    end,
                    chromosome,
                    jobs,
                    technicians
                )

                if conflict:

                    continue

                chromosome[job_index] = (
                    technician_id,
                    start
                )

                if backtrack(position + 1):

                    return True

                chromosome[job_index] = None

        return False

    success = backtrack(0)

    if success:

        return chromosome

    return None


# ================================================================
# REPAIR CHROMOSOME
# ================================================================

def repair_chromosome(
    chromosome,
    jobs,
    technicians,
    ai_decisions
):

    # ------------------------------------------------------------
    # Important:
    # Instead of trying to patch only the conflicting technician,
    # rebuild a globally feasible assignment.
    #
    # Jobs with higher AI priority are assigned first.
    # ------------------------------------------------------------

    job_order = list(
        range(len(jobs))
    )

    job_order.sort(
        key=lambda index: (
            -calculate_ai_priority(
                jobs[index],
                ai_decisions
            ),
            -priority_score(
                jobs[index]["priority"]
            ),
            -criticality_score(
                jobs[index]["criticality"]
            )
        )
    )

    feasible = find_feasible_assignment(
        jobs,
        technicians,
        job_order
    )

    if feasible is not None:

        return feasible

    # ------------------------------------------------------------
    # If no globally feasible solution is found,
    # return the original chromosome.
    # ------------------------------------------------------------

    return chromosome


# ================================================================
# CREATE INITIAL POPULATION
# ================================================================

def create_population(
    jobs,
    technicians,
    ai_decisions,
    population_size
):

    population = []

    # First chromosome = guaranteed feasible solution
    priority_order = list(
        range(len(jobs))
    )

    priority_order.sort(
        key=lambda index: (
            -calculate_ai_priority(
                jobs[index],
                ai_decisions
            ),
            -priority_score(
                jobs[index]["priority"]
            ),
            -criticality_score(
                jobs[index]["criticality"]
            )
        )
    )

    feasible = find_feasible_assignment(
        jobs,
        technicians,
        priority_order
    )

    if feasible is not None:

        population.append(
            feasible
        )

    # Other chromosomes
    while len(population) < population_size:

        chromosome = create_random_chromosome(
            jobs,
            technicians
        )

        chromosome = repair_chromosome(
            chromosome,
            jobs,
            technicians,
            ai_decisions
        )

        population.append(
            chromosome
        )

    return population


# ================================================================
# TOURNAMENT SELECTION
# ================================================================

def tournament_selection(
    population,
    jobs,
    technicians,
    ai_decisions,
    requirements,
    spares
):

    tournament_size = min(
        4,
        len(population)
    )

    candidates = random.sample(
        population,
        tournament_size
    )

    candidates.sort(
        key=lambda chromosome: fitness(
            chromosome,
            jobs,
            technicians,
            ai_decisions,
            requirements,
            spares
        ),
        reverse=True
    )

    return candidates[0]


# ================================================================
# CROSSOVER
# ================================================================

def crossover(
    parent1,
    parent2
):

    if len(parent1) <= 1:

        return parent1[:]

    point = random.randint(
        1,
        len(parent1) - 1
    )

    child = (
        parent1[:point]
        +
        parent2[point:]
    )

    return child


# ================================================================
# MUTATION
# ================================================================

def mutation(
    chromosome,
    jobs,
    technicians
):

    mutated = chromosome[:]

    mutation_rate = 0.20

    for job_index in range(
        len(jobs)
    ):

        if random.random() > mutation_rate:

            continue

        job = jobs[job_index]

        specialists = [
            technician
            for technician in technicians
            if specialization_matches(
                job,
                technician
            )
        ]

        if not specialists:

            specialists = technicians

        technician = random.choice(
            specialists
        )

        duration = get_duration(job)

        possible_starts = list(
            range(
                9 * 60,
                18 * 60 - duration + 1,
                30
            )
        )

        if not possible_starts:

            continue

        start = random.choice(
            possible_starts
        )

        mutated[job_index] = (
            technician["technician_id"],
            start
        )

    return mutated


# ================================================================
# GENETIC ALGORITHM
# ================================================================

def genetic_algorithm(
    jobs,
    technicians,
    ai_decisions,
    requirements,
    spares
):

    population_size = 60

    generations = 150

    population = create_population(
        jobs,
        technicians,
        ai_decisions,
        population_size
    )

    best_chromosome = None

    best_fitness = float("-inf")

    for generation in range(
        generations
    ):

        # --------------------------------------------------------
        # Evaluate population
        # --------------------------------------------------------

        scored_population = []

        for chromosome in population:

            score = fitness(
                chromosome,
                jobs,
                technicians,
                ai_decisions,
                requirements,
                spares
            )

            scored_population.append(
                (
                    score,
                    chromosome
                )
            )

            if score > best_fitness:

                best_fitness = score

                best_chromosome = (
                    chromosome[:]
                )

        # --------------------------------------------------------
        # Elitism
        # --------------------------------------------------------

        scored_population.sort(
            key=lambda item: item[0],
            reverse=True
        )

        new_population = [
            scored_population[0][1][:],
            scored_population[1][1][:]
        ]

        # --------------------------------------------------------
        # Generate children
        # --------------------------------------------------------

        while len(
            new_population
        ) < population_size:

            parent1 = tournament_selection(
                population,
                jobs,
                technicians,
                ai_decisions,
                requirements,
                spares
            )

            parent2 = tournament_selection(
                population,
                jobs,
                technicians,
                ai_decisions,
                requirements,
                spares
            )

            child = crossover(
                parent1,
                parent2
            )

            child = mutation(
                child,
                jobs,
                technicians
            )

            # Repair every child
            child = repair_chromosome(
                child,
                jobs,
                technicians,
                ai_decisions
            )

            new_population.append(
                child
            )

        population = new_population

    # ------------------------------------------------------------
    # Final repair
    # ------------------------------------------------------------

    best_chromosome = repair_chromosome(
        best_chromosome,
        jobs,
        technicians,
        ai_decisions
    )

    best_fitness = fitness(
        best_chromosome,
        jobs,
        technicians,
        ai_decisions,
        requirements,
        spares
    )

    return (
        best_chromosome,
        best_fitness
    )


# ================================================================
# CHECK FINAL CONFLICTS
# ================================================================

def check_conflicts(
    chromosome,
    jobs
):

    conflicts = []

    for i in range(
        len(jobs)
    ):

        technician_i = chromosome[i][0]
        start_i = chromosome[i][1]
        end_i = start_i + get_duration(
            jobs[i]
        )

        for j in range(
            i + 1,
            len(jobs)
        ):

            technician_j = chromosome[j][0]
            start_j = chromosome[j][1]
            end_j = start_j + get_duration(
                jobs[j]
            )

            if technician_i == technician_j:

                if (
                    start_i < end_j
                    and
                    start_j < end_i
                ):

                    conflicts.append(
                        (
                            jobs[i],
                            jobs[j],
                            technician_i
                        )
                    )

    return conflicts


# ================================================================
# PRINT SCHEDULE
# ================================================================

def print_schedule(
    chromosome,
    jobs,
    technicians,
    ai_decisions
):

    print()
    print("=" * 70)
    print("OPTIMIZED MAINTENANCE SCHEDULE")
    print("=" * 70)

    # Sort jobs by scheduled start time
    order = sorted(
        range(len(jobs)),
        key=lambda index: (
            chromosome[index][1],
            -calculate_ai_priority(
                jobs[index],
                ai_decisions
            )
        )
    )

    for job_index in order:

        job = jobs[job_index]

        technician_id = chromosome[
            job_index
        ][0]

        start = chromosome[
            job_index
        ][1]

        end = (
            start
            +
            get_duration(job)
        )

        technician = get_technician(
            technicians,
            technician_id
        )

        decision = ai_decisions.get(
            job["machine_id"]
        )

        if decision:

            failure_risk = float(
                decision["failure_risk"]
            )

            urgency_score = float(
                decision["urgency_score"]
            )

            ai_priority = calculate_ai_priority(
                job,
                ai_decisions
            )

        else:

            failure_risk = 0.0
            urgency_score = 0.0
            ai_priority = 0.0

        original_start = time_to_minutes(
            job["start_time"]
        )

        time_changed = (
            start != original_start
        )

        print()
        print(
            f"Maintenance ID : "
            f"{job['maintenance_id']}"
        )

        print(
            f"Machine         : "
            f"{job['machine_name']}"
        )

        print(
            f"Maintenance     : "
            f"{job['maintenance_type']}"
        )

        print(
            f"Date            : "
            f"{job['scheduled_date']}"
        )

        print(
            f"Time            : "
            f"{format_time(start)} - "
            f"{format_time(end)}"
        )

        if time_changed:

            print(
                f"Original Time   : "
                f"{format_time(original_start)} - "
                f"{format_time(original_start + get_duration(job))}"
            )

            print(
                "Schedule Change : Time adjusted "
                "to satisfy constraints"
            )

        print(
            f"Priority        : "
            f"{job['priority']}"
        )

        print(
            f"Criticality     : "
            f"{job['criticality']}"
        )

        print(
            f"Failure Risk    : "
            f"{failure_risk:.2f}%"
        )

        print(
            f"Urgency Score   : "
            f"{urgency_score:.2f}"
        )

        print(
            f"AI Priority     : "
            f"{ai_priority:.2f}"
        )

        print(
            f"Technician      : "
            f"{technician['technician_name']}"
        )

        print(
            f"Specialization  : "
            f"{technician['specialization']}"
        )

        print("-" * 70)


# ================================================================
# FINAL FEASIBILITY CHECK
# ================================================================

def final_feasibility_check(
    chromosome,
    jobs,
    technicians
):

    print()
    print("=" * 70)
    print("FEASIBILITY CHECK")
    print("=" * 70)

    conflicts = check_conflicts(
        chromosome,
        jobs
    )

    if not conflicts:

        print()
        print(
            "SUCCESS: No technician time conflicts found!"
        )

    else:

        print()
        print(
            "ERROR: Technician time conflicts found!"
        )

        for job1, job2, technician_id in conflicts:

            technician = get_technician(
                technicians,
                technician_id
            )

            print()
            print(
                f"Technician : "
                f"{technician['technician_name']}"
            )

            print(
                f"Job 1      : "
                f"{job1['machine_name']} "
                f"{job1['start_time']} - "
                f"{job1['end_time']}"
            )

            print(
                f"Job 2      : "
                f"{job2['machine_name']} "
                f"{job2['start_time']} - "
                f"{job2['end_time']}"
            )

            print(
                "CONFLICT DETECTED"
            )

    # ------------------------------------------------------------
    # Working hours
    # ------------------------------------------------------------

    working_hour_error = False

    for index, job in enumerate(jobs):

        start = chromosome[index][1]

        end = start + get_duration(job)

        if (
            start < 9 * 60
            or
            end > 18 * 60
        ):

            working_hour_error = True

            print()
            print(
                f"ERROR: {job['machine_name']} "
                f"is outside working hours."
            )

    if not working_hour_error:

        print(
            "SUCCESS: All jobs are within "
            "09:00 - 18:00 working hours."
        )

    return (
        len(conflicts) == 0
        and
        not working_hour_error
    )


# ================================================================
# FINAL VALIDATION
# ================================================================

def final_validation(
    chromosome,
    jobs,
    technicians
):

    print()
    print("=" * 70)
    print("FINAL VALIDATION")
    print("=" * 70)

    conflicts = check_conflicts(
        chromosome,
        jobs
    )

    if len(conflicts) == 0:

        print()
        print(
            "SUCCESS: Optimized schedule is "
            "conflict-free!"
        )

        print(
            "SUCCESS: Technician assignments "
            "are feasible."
        )

        print(
            "SUCCESS: Schedule optimization completed."
        )

        return True

    else:

        print()
        print(
            f"ERROR: {len(conflicts)} "
            "conflict(s) remain."
        )

        for job1, job2, technician_id in conflicts:

            technician = get_technician(
                technicians,
                technician_id
            )

            print(
                f"Conflict: "
                f"{job1['machine_name']} vs "
                f"{job2['machine_name']} "
                f"for {technician['technician_name']}"
            )

        return False


# ================================================================
# SAVE OPTIMIZED SCHEDULE TO MYSQL
# ================================================================

def save_optimized_schedule(
    connection,
    scheduled_jobs,
    chromosome,
    blocked_jobs
):

    print()
    print("=" * 70)
    print("SAVING OPTIMIZED SCHEDULE TO MYSQL")
    print("=" * 70)

    cursor = connection.cursor()

    # ------------------------------------------------------------
    # SAVE jobs that were successfully optimized by the GA
    # ------------------------------------------------------------

    for index, job in enumerate(scheduled_jobs):

        assignment = chromosome[index]

        maintenance_id = job["maintenance_id"]

        if assignment is None:

            cursor.execute(
                """
                UPDATE MAINTENANCE
                SET
                    technician_id = NULL,
                    scheduled_date = NULL,
                    start_time = NULL,
                    end_time = NULL,
                    status = 'Blocked',
                    notes = %s
                WHERE maintenance_id = %s
                """,
                (
                    "Blocked by AI optimization.",
                    maintenance_id
                )
            )

            print(
                f"BLOCKED | Maintenance ID {maintenance_id} | "
                f"{job['machine_name']}"
            )

            continue

        technician_id = assignment[0]
        start_minutes = assignment[1]

        duration = get_duration(job)

        end_minutes = (
            start_minutes + duration
        )

        start_time = time(
            start_minutes // 60,
            start_minutes % 60
        )

        end_time = time(
            end_minutes // 60,
            end_minutes % 60
        )

        cursor.execute(
            """
            UPDATE MAINTENANCE
            SET
                technician_id = %s,
                scheduled_date = %s,
                start_time = %s,
                end_time = %s,
                status = 'Planned',
                notes = %s
            WHERE maintenance_id = %s
            """,
            (
                technician_id,
                job["scheduled_date"],
                start_time,
                end_time,
                "AI-optimized schedule generated "
                "by Genetic Algorithm.",
                maintenance_id
            )
        )

        print(
            f"SAVED | Maintenance ID {maintenance_id} | "
            f"{job['machine_name']} | "
            f"{start_time} - {end_time}"
        )

    # ------------------------------------------------------------
    # Save jobs blocked by the HARD spare-part constraint
    # ------------------------------------------------------------

    print()

    for blocked in blocked_jobs:

        job = blocked["job"]

        maintenance_id = job["maintenance_id"]

        cursor.execute(
            """
            UPDATE MAINTENANCE
            SET
                technician_id = NULL,
                scheduled_date = NULL,
                start_time = NULL,
                end_time = NULL,
                status = 'Blocked',
                notes = %s
            WHERE maintenance_id = %s
            """,
            (
                "Blocked by AI optimization: "
                "required spare part unavailable.",
                maintenance_id
            )
        )

        print(
            f"BLOCKED | Maintenance ID {maintenance_id} | "
            f"{job['machine_name']} | "
            f"Spare unavailable"
        )

    connection.commit()

    cursor.close()

    print()
    print("SUCCESS: Optimized schedule saved to MySQL.")


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 70)
    print("AI MAINTENANCE OPTIMIZER")
    print("GENETIC ALGORITHM SCHEDULER")
    print("=" * 70)

    connection = connect_db()

    if connection is None:
        return

    try:

        # --------------------------------------------------------
        # Load data
        # --------------------------------------------------------

        jobs = get_jobs(connection)

        technicians = get_technicians(connection)

        ai_decisions = get_latest_ai_decisions(
            connection
        )

        requirements = get_requirements(
            connection
        )

        spares = get_spares(
            connection
        )

        print()
        print(
            f"Maintenance jobs found : "
            f"{len(jobs)}"
        )

        print(
            f"Technicians available   : "
            f"{len(technicians)}"
        )

        print(
            f"AI decisions available  : "
            f"{len(ai_decisions)}"
        )

        print(
            f"Spare parts found       : "
            f"{len(spares)}"
        )

        # --------------------------------------------------------
        # AI priority
        # --------------------------------------------------------

        print()
        print("=" * 70)
        print("AI PRIORITY OF MAINTENANCE JOBS")
        print("=" * 70)

        for job in jobs:

            ai_priority = calculate_ai_priority(
                job,
                ai_decisions
            )

            print(
                f"ID {job['maintenance_id']} | "
                f"{job['machine_name']} | "
                f"AI Priority = "
                f"{ai_priority:.2f}"
            )

        # --------------------------------------------------------
        # HARD SPARE CONSTRAINT
        # --------------------------------------------------------

        (
            eligible_jobs,
            blocked_jobs
        ) = filter_jobs_by_spare_availability(
            jobs,
            requirements,
            spares,
            ai_decisions
        )

        print()
        print("=" * 70)
        print("SPARE-PART CONSTRAINT CHECK")
        print("=" * 70)

        print()
        print(
            f"Jobs eligible for GA : "
            f"{len(eligible_jobs)}"
        )

        print(
            f"Jobs blocked by spare constraint : "
            f"{len(blocked_jobs)}"
        )

        for blocked in blocked_jobs:

            job = blocked["job"]

            print()
            print(
                f"BLOCKED | ID {job['maintenance_id']} | "
                f"{job['machine_name']} | "
                f"{job['maintenance_type']}"
            )

            requirement = get_job_requirement(
                job,
                requirements
            )

            spare_name = "Unknown"

            if requirement is not None:

                for spare in spares:

                    if (
                        spare["spare_part_id"]
                        == requirement["spare_part_id"]
                    ):

                        spare_name = spare[
                            "part_name"
                        ]

                        break

            print(
                f"    Spare Part : {spare_name}"
            )

            print(
                f"    Required   : "
                f"{blocked['required_quantity']}"
            )

            print(
                f"    Available  : "
                f"{blocked['available_quantity']}"
            )

            print(
                "    Reason     : "
                "Insufficient spare stock."
            )

        # --------------------------------------------------------
        # Run GA ONLY on jobs satisfying spare constraints
        # --------------------------------------------------------

        print()
        print("=" * 70)
        print("RUNNING GENETIC ALGORITHM")
        print("=" * 70)

        if eligible_jobs:

            (
                best_chromosome,
                best_fitness
            ) = genetic_algorithm(
                eligible_jobs,
                technicians,
                ai_decisions,
                requirements,
                spares
            )

            print()
            print(
                f"Best Fitness = "
                f"{best_fitness:.2f}"
            )

            # ----------------------------------------------------
            # Print optimized schedule
            # ----------------------------------------------------

            print_schedule(
                best_chromosome,
                eligible_jobs,
                technicians,
                ai_decisions
            )

            # ----------------------------------------------------
            # Feasibility
            # ----------------------------------------------------

            feasible = final_feasibility_check(
                best_chromosome,
                eligible_jobs,
                technicians
            )

            # ----------------------------------------------------
            # Final validation
            # ----------------------------------------------------

            validated = final_validation(
                best_chromosome,
                eligible_jobs,
                technicians
            )

        else:

            best_chromosome = []

            best_fitness = 0

            feasible = True

            validated = True

            print()
            print(
                "No jobs are eligible for the "
                "Genetic Algorithm."
            )

        # --------------------------------------------------------
        # Unscheduled jobs
        # --------------------------------------------------------

        print()
        print("=" * 70)
        print("UNSCHEDULED JOBS")
        print("=" * 70)

        if blocked_jobs:

            for blocked in blocked_jobs:

                job = blocked["job"]

                requirement = get_job_requirement(
                    job,
                    requirements
                )

                spare_name = "Required spare part"

                if requirement is not None:

                    for spare in spares:

                        if (
                            spare["spare_part_id"]
                            == requirement["spare_part_id"]
                        ):

                            spare_name = spare[
                                "part_name"
                            ]

                            break

                print()
                print(
                    f"Maintenance ID : "
                    f"{job['maintenance_id']}"
                )

                print(
                    f"Machine         : "
                    f"{job['machine_name']}"
                )

                print(
                    f"Maintenance     : "
                    f"{job['maintenance_type']}"
                )

                print(
                    "Status          : NOT SCHEDULED"
                )

                print(
                    f"Reason          : "
                    f"{spare_name} unavailable"
                )

        else:

            print()
            print(
                "No jobs were blocked by spare constraints."
            )

        # --------------------------------------------------------
        # Final result
        # --------------------------------------------------------

        print()
        print("=" * 70)
        print("GENETIC ALGORITHM COMPLETED")
        print("=" * 70)

        if feasible and validated:

            print()
            print(
                "FINAL RESULT: SUCCESS"
            )

            print(
                "The optimized schedule is "
                "feasible and conflict-free."
            )

        else:

            print()
            print(
                "FINAL RESULT: REVIEW REQUIRED"
            )

        # --------------------------------------------------------
        # Save to existing MAINTENANCE table
        # --------------------------------------------------------

        if feasible and validated:

            save_optimized_schedule(
                connection,
                eligible_jobs,
                best_chromosome,
                blocked_jobs
            )

    finally:

        connection.close()

        print()
        print(
            "MySQL connection closed."
        )


# ================================================================
# PROGRAM START
# ================================================================

if __name__ == "__main__":

    main()