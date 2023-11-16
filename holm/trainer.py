import torch
from tqdm import tqdm
from transformers import get_linear_schedule_with_warmup
from geoopt.optim import RiemannianAdam, RiemannianSGD
from .taxonomy import TaxonomyTrainingDataset
from .old_model import HyperOntoEmbedfromLM
from deeponto.onto import Taxonomy


class HyperOntoEmbedTrainer:
    def __init__(
        self,
        taxonomy: Taxonomy,
        training_subsumptions: list,
        embed_dim: int = 50,
        n_negative_samples: int = 10,
        batch_size: int = 50,
        learning_rate: float = 0.01,
        n_epochs: int = 200,
        n_warmup_epochs: int = 10,
        gpu_device: int = 0,
    ):
        self.dataset = TaxonomyTrainingDataset(taxonomy, training_subsumptions, n_negative_samples)
        self.batch_size = batch_size
        self.dataloader = torch.utils.data.DataLoader(
            self.dataset, self.batch_size, shuffle=True, pin_memory=True, num_workers=10
        )
        self.learning_rate = learning_rate

        # self.device = torch.device(f"cuda:{gpu_device}" if torch.cuda.is_available() else "cpu")
        self.model = HyperOntoEmbedfromLM(taxonomy, embed_dim=embed_dim, gpu_device=gpu_device)

        self.optimizer = RiemannianAdam(self.model.parameters(), lr=self.learning_rate)
        self.current_epoch = 0
        self.n_epochs = n_epochs
        self.n_epoch_steps = len(self.dataloader)
        self.n_trainining_steps = self.n_epoch_steps * self.n_epochs
        self.warmup_epochs = n_warmup_epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=self.warmup_epochs * self.n_epoch_steps,  # one epoch warming-up
            num_training_steps=self.n_trainining_steps,
        )

    @property
    def lr(self):
        for g in self.optimizer.param_groups:
            return g["lr"]

    def training_step(self, subject, objects, loss_func):
        # batch = batch.to(self.device)
        self.optimizer.zero_grad(set_to_none=True)
        preds = self.model(subject, *objects)
        loss = loss_func(preds)
        loss.backward()
        self.optimizer.step()
        self.scheduler.step()
        return loss

    def training_epoch(self, loss_func, save_at_epoch=True):
        epoch_bar = tqdm(range(self.n_epoch_steps), desc=f"Epoch {self.current_epoch + 1}", leave=True, unit="batch")
        # # change to uniform negative sampling after warm starting (or burn-in)
        # if self.current_epoch >= self.warmup_epochs:
        #     self.dataloader = self.get_dataloader(weighted_negative_sampling=False)
        # running_loss = 0.0
        for batch in self.dataloader:
            subject = batch.subject
            objects = list(zip(batch.object, *batch.negative_objects))
            loss = self.training_step(subject, objects, loss_func)
            # running_loss += loss
            epoch_bar.set_postfix({"loss": loss.item(), "lr": self.lr})
            epoch_bar.update()
        self.current_epoch += 1
        # if save_at_epoch:
        #     torch.save(self.model, f"experiments/poincare.{dim}d.pt")

    def run(self):
        for _ in range(self.n_epochs):
            self.training_epoch(self.dist_loss)

    def save(self, output_dir: str):
        pass
