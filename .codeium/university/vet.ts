enum Treatment {
    ANNUAL_CHECKUP = "checkup",
    SURGERY = "surgery",
}

class Vet {
    constructor(
        public name: string,
        public treatmentTypes: Treatment[],
        public yearsOfExperience: number
    ) { }

    /**
     * A function that treats a pet.
     *
     * @param {Pet} pet - The pet to be treated.
     * @return {number} The calculated treatment cost.
     */
    treatPet(pet: Pet, treatments: Treatment[]): number {
        console.log("Treating:", pet.name, "with:", treatments);
        let cost = 0;
        treatments.forEach((treatment) => {
            if (treatment === Treatment.ANNUAL_CHECKUP) {
                cost += 100;
            } else if (treatment === Treatment.SURGERY) {
                cost += 500;
            }
        });
        return cost;
    }

    displayVetInfo(): void {
        console.log(`Vet: ${this.name}`);
        console.log(`Specialties: ${this.specialties.join(", ")}`);
        console.log(`Years of Experience: ${this.yearsOfExperience}`);
    }
}
